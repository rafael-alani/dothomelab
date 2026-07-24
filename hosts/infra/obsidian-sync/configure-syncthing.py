#!/usr/bin/env python3
import json
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


CONFIG = Path("/srv/appdata/docker/syncthing/config/config.xml")
BASE_URL = "http://127.0.0.1:8384"
FOLDER_ID = "obsidian-vault"


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


def get_or_default_folder(api_key: str):
    try:
        return request(api_key, "GET", f"/rest/config/folders/{FOLDER_ID}"), True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    return request(api_key, "GET", "/rest/config/defaults/folder"), False


def wait_for_api(api_key: str) -> None:
    for _ in range(30):
        try:
            request(api_key, "GET", "/rest/system/ping")
            return
        except urllib.error.URLError:
            time.sleep(1)
    raise RuntimeError("Syncthing API did not return after its configuration reload")


def main() -> int:
    api_key = wait_for_config()
    folder, exists = get_or_default_folder(api_key)
    folder.update(
        {
            "id": FOLDER_ID,
            "label": "Obsidian Vault",
            "path": "/vault",
            "type": "receiveonly",
            "ignoreDelete": False,
            "paused": False,
            "fsWatcherEnabled": True,
            "rescanIntervalS": 3600,
            "versioning": {
                "type": "staggered",
                "params": {"maxAge": "31536000"},
                "cleanupIntervalS": 3600,
                "fsPath": "/versions",
                "fsType": "basic",
            },
        }
    )

    if exists:
        request(api_key, "PUT", f"/rest/config/folders/{FOLDER_ID}", folder)
    else:
        request(api_key, "POST", "/rest/config/folders", folder)

    gui = request(api_key, "GET", "/rest/config/gui")
    gui["insecureAdminAccess"] = False
    # NPM is host-networked and proxies the loopback-only GUI with its public
    # hostname. Authentication remains required once the user sets credentials.
    gui["insecureSkipHostcheck"] = True
    request(api_key, "PUT", "/rest/config/gui", gui)

    # Updating GUI settings restarts the API listener without restarting the
    # process, so wait for it before asking whether a full restart is needed.
    wait_for_api(api_key)
    restart_state = request(api_key, "GET", "/rest/config/restart-required")
    if restart_state.get("requiresRestart", False):
        try:
            request(api_key, "POST", "/rest/system/restart")
        except (urllib.error.URLError, ConnectionResetError):
            pass

    print(
        "Configured obsidian-vault as Receive Only with 365-day staggered "
        "versions at /versions"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Syncthing configuration failed: {exc}", file=sys.stderr)
        raise
