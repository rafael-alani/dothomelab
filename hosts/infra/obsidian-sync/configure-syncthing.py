#!/usr/bin/env python3
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


CONFIG = Path("/srv/appdata/docker/syncthing/config/config.xml")
BASE_URL = "http://127.0.0.1:8384"
DEFAULT_FOLDER_ID = "obsidian-vault"
FOLDER_PATH = "/vault/shared/media/obsidian"
VERSIONS_PATH = "/vault/shared/media/.obsidian-versions"
LEGACY_FOLDER_PATH = "/vault"
VAULT = Path(FOLDER_PATH)


def wait_for_config() -> str:
    for _ in range(60):
        if CONFIG.is_file():
            root = ET.parse(CONFIG).getroot()
            api_key = root.findtext("./gui/apikey")
            if api_key:
                return api_key
        time.sleep(1)
    raise RuntimeError(f"Syncthing configuration did not appear at {CONFIG}")


def request(api_key: str, method: str, path: str, payload=None):
    body = None
    headers = {"X-API-Key": api_key}
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        content = response.read()
        return json.loads(content) if content else None


def get_or_default_folder(api_key: str, folder_id: str):
    try:
        return request(api_key, "GET", f"/rest/config/folders/{folder_id}"), True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    return request(api_key, "GET", "/rest/config/defaults/folder"), False


def wait_for_api(api_key: str) -> None:
    for _ in range(30):
        try:
            request(api_key, "GET", "/rest/system/ping")
            return
        except (
            ConnectionResetError,
            http.client.RemoteDisconnected,
            urllib.error.URLError,
        ):
            time.sleep(1)
    raise RuntimeError("Syncthing API did not return after its configuration reload")


def remove_unused_placeholder(api_key: str, folder_id: str) -> None:
    if folder_id == DEFAULT_FOLDER_ID:
        return
    try:
        placeholder = request(
            api_key, "GET", f"/rest/config/folders/{DEFAULT_FOLDER_ID}"
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return
        raise

    allowed_entries = {".stfolder", ".stignore"}
    vault_entries = {entry.name for entry in VAULT.iterdir()}
    if (
        placeholder.get("path") not in {LEGACY_FOLDER_PATH, FOLDER_PATH}
        or len(placeholder.get("devices", [])) > 1
        or not vault_entries.issubset(allowed_entries)
    ):
        raise RuntimeError(
            "Refusing to replace obsidian-vault: it is paired or the vault "
            "contains data. Change the folder ID manually with a fresh backup."
        )

    request(
        api_key, "DELETE", f"/rest/config/folders/{DEFAULT_FOLDER_ID}"
    )
    print(
        f"Replaced unused placeholder {DEFAULT_FOLDER_ID} with existing "
        f"folder ID {folder_id}"
    )


def pending_offer_devices(api_key: str, folder_id: str) -> list[str]:
    pending = request(api_key, "GET", "/rest/cluster/pending/folders")
    offered_by = pending.get(folder_id, {}).get("offeredBy", {})
    if not offered_by:
        return []

    configured_devices = {
        device.get("deviceID")
        for device in request(api_key, "GET", "/rest/config/devices")
    }
    unknown_devices = set(offered_by) - configured_devices
    if unknown_devices:
        raise RuntimeError(
            f"Folder {folder_id} was offered by an unknown device; add and "
            "verify that device before accepting the folder"
        )
    return sorted(offered_by)


def add_folder_devices(folder: dict, device_ids: list[str]) -> None:
    folder_devices = folder.setdefault("devices", [])
    folder_device_ids = {device.get("deviceID") for device in folder_devices}
    for device_id in device_ids:
        if device_id not in folder_device_ids:
            folder_devices.append(
                {
                    "deviceID": device_id,
                    "encryptionPassword": "",
                    "introducedBy": "",
                }
            )


def configure_gui(api_key: str) -> bool:
    gui = request(api_key, "GET", "/rest/config/gui")
    current_user = gui.get("user", "")
    current_password = gui.get("password", "")
    requested_user = os.environ.get("SYNCTHING_GUI_USERNAME", "")
    requested_password = os.environ.get("SYNCTHING_GUI_PASSWORD", "")

    if bool(current_user) != bool(current_password):
        raise RuntimeError(
            "Syncthing GUI has only one credential field configured; refusing "
            "to replace partial authentication state"
        )

    configured_auth = bool(current_user and current_password)
    if configured_auth:
        if requested_user and requested_user != current_user:
            raise RuntimeError(
                "SYNCTHING_GUI_USERNAME differs from the configured GUI user; "
                "rotate credentials as a separate task"
            )
    else:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", requested_user):
            raise RuntimeError(
                "SYNCTHING_GUI_USERNAME must contain 1-64 letters, numbers, "
                "dot, underscore, or hyphen"
            )
        if len(requested_password) < 32:
            raise RuntimeError(
                "SYNCTHING_GUI_PASSWORD must contain at least 32 characters"
            )
        gui["user"] = requested_user
        gui["password"] = requested_password
        gui["authMode"] = "static"

    gui["insecureAdminAccess"] = False
    # NPM is host-networked and supplies the external host name to this
    # loopback-only listener. The NPM route and GUI authentication are both
    # required before this exception is safe.
    gui["insecureSkipHostcheck"] = True
    try:
        request(api_key, "PUT", "/rest/config/gui", gui)
    except (
        ConnectionResetError,
        http.client.RemoteDisconnected,
        urllib.error.URLError,
    ):
        pass

    wait_for_api(api_key)
    applied = request(api_key, "GET", "/rest/config/gui")
    if applied.get("user") != (current_user or requested_user):
        raise RuntimeError("Syncthing GUI username was not applied")
    password_hash = applied.get("password", "")
    if not re.fullmatch(r"\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}", password_hash):
        raise RuntimeError("Syncthing GUI password was not stored as a bcrypt hash")
    if applied.get("insecureAdminAccess", False):
        raise RuntimeError("Syncthing insecure admin access must remain disabled")
    if not applied.get("insecureSkipHostcheck", False):
        raise RuntimeError("Syncthing reverse-proxy host check exception is missing")
    return not configured_auth


def main() -> int:
    folder_id = sys.argv[1] if len(sys.argv) == 2 else DEFAULT_FOLDER_ID
    if len(sys.argv) > 2 or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", folder_id):
        raise ValueError(
            "Usage: configure-syncthing.py [existing-folder-id]; folder IDs "
            "may contain letters, numbers, dot, underscore, and hyphen"
        )

    api_key = wait_for_config()
    offering_devices = pending_offer_devices(api_key, folder_id)
    remove_unused_placeholder(api_key, folder_id)
    folder, exists = get_or_default_folder(api_key, folder_id)
    add_folder_devices(folder, offering_devices)
    folder.update(
        {
            "id": folder_id,
            "label": "Obsidian Vault",
            "path": FOLDER_PATH,
            "type": "receiveonly",
            "ignoreDelete": False,
            "paused": False,
            "fsWatcherEnabled": True,
            "rescanIntervalS": 3600,
            "versioning": {
                "type": "staggered",
                "params": {"maxAge": "31536000"},
                "cleanupIntervalS": 3600,
                "fsPath": VERSIONS_PATH,
                "fsType": "basic",
            },
        }
    )

    if exists:
        request(api_key, "PUT", f"/rest/config/folders/{folder_id}", folder)
    else:
        request(api_key, "POST", "/rest/config/folders", folder)

    auth_added = configure_gui(api_key)
    restart_state = request(api_key, "GET", "/rest/config/restart-required")
    if restart_state.get("requiresRestart", False):
        try:
            request(api_key, "POST", "/rest/system/restart")
        except (urllib.error.URLError, ConnectionResetError):
            pass

    print(
        f"Configured {folder_id} as Receive Only with 365-day staggered "
        f"versions at {VERSIONS_PATH}"
    )
    if offering_devices:
        print(
            f"Accepted the pending folder offer from {len(offering_devices)} "
            "configured device(s)"
        )
    if auth_added:
        print("Configured Syncthing GUI authentication without displaying credentials")
    else:
        print("Preserved existing Syncthing GUI authentication")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Syncthing configuration failed: {exc}", file=sys.stderr)
        raise
