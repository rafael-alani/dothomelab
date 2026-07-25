#!/usr/bin/env python3
"""Reconcile Shelfarr's scoped Audiobookshelf integration without displaying secrets."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import string
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENV_KEY = "AUDIOBOOKSHELF_SHELFARR_API_KEY"
INTEGRATION_USERNAME = "shelfarr-integration"
API_KEY_NAME = "Shelfarr audiobook library scan"
EXPECTED_LIBRARY_PATH = "/audiobooks"
EXPECTED_SCAN_CRON = "0 4 * * *"
PERMISSIONS = {
    "download": False,
    "update": False,
    "delete": False,
    "upload": False,
    "createEreader": False,
    "accessAllLibraries": False,
    "accessAllTags": False,
    "accessExplicitContent": False,
    "selectedTagsNotAccessible": False,
}


class ReconcileError(RuntimeError):
    """A sanitized reconciliation failure that never includes credentials."""


def parse_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip():
            values[key.strip()] = value
    return values


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
        text=True,
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def update_env(path: Path, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replaced = False
    updated: list[str] = []
    for line in lines:
        if (
            "=" in line
            and not line.lstrip().startswith("#")
            and line.split("=", 1)[0].strip() == ENV_KEY
        ):
            updated.append(f"{ENV_KEY}={value}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        if updated and updated[-1] != "":
            updated.append("")
        updated.extend(
            [
                "# Shelfarr Audiobookshelf integration (generated; do not commit).",
                f"{ENV_KEY}={value}",
            ]
        )
    write_atomic(path, "\n".join(updated) + "\n")


def api_request(
    base_url: str,
    token: str,
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{endpoint}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise ReconcileError(
            f"Audiobookshelf {method} {endpoint} returned HTTP {error.code}"
        ) from None
    except urllib.error.URLError as error:
        raise ReconcileError(
            f"Audiobookshelf {method} {endpoint} could not be reached"
        ) from error
    if not body:
        return {}
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as error:
        raise ReconcileError(
            f"Audiobookshelf {method} {endpoint} returned invalid JSON"
        ) from error
    if not isinstance(decoded, dict):
        raise ReconcileError(
            f"Audiobookshelf {method} {endpoint} returned an unexpected payload"
        )
    return decoded


def root_token(ctid: int, container: str) -> str:
    javascript = r"""
const sqlite3 = require("/app/node_modules/sqlite3");
const database = new sqlite3.Database(
  "/config/absdatabase.sqlite",
  sqlite3.OPEN_READONLY,
  (openError) => {
    if (openError) throw openError;
    database.get(
      "SELECT token FROM users WHERE type = 'root' LIMIT 1",
      (queryError, row) => {
        if (queryError) throw queryError;
        if (!row || !row.token) process.exit(2);
        process.stdout.write(row.token);
        database.close((closeError) => {
          if (closeError) throw closeError;
        });
      },
    );
  },
);
"""
    result = subprocess.run(
        [
            "pct",
            "exec",
            str(ctid),
            "--",
            "docker",
            "exec",
            container,
            "node",
            "-e",
            javascript,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    token = result.stdout.strip()
    if result.returncode or not token:
        raise ReconcileError(
            "Audiobookshelf root API credential could not be read from its "
            "canonical application database"
        )
    return token


def select_audiobook_library(
    base_url: str, token: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    libraries = api_request(base_url, token, "GET", "/api/libraries").get(
        "libraries", []
    )
    if not isinstance(libraries, list):
        raise ReconcileError("Audiobookshelf returned an invalid library list")
    matches = [
        library
        for library in libraries
        if library.get("mediaType") == "book"
        and any(
            folder.get("fullPath") == EXPECTED_LIBRARY_PATH
            for folder in library.get("folders", [])
            if isinstance(folder, dict)
        )
    ]
    if len(matches) != 1:
        raise ReconcileError(
            "Audiobookshelf must expose exactly one book library rooted at "
            f"{EXPECTED_LIBRARY_PATH}"
        )
    return matches[0], libraries


def expected_user_payload(library_id: str) -> dict[str, Any]:
    return {
        "type": "admin",
        "isActive": True,
        "permissions": PERMISSIONS,
        "librariesAccessible": [library_id],
    }


def validate_user(user: dict[str, Any], library_id: str) -> None:
    permissions = user.get("permissions", {})
    if user.get("type") != "admin" or not user.get("isActive"):
        raise ReconcileError("Shelfarr Audiobookshelf integration user drifted")
    for key, expected in PERMISSIONS.items():
        if permissions.get(key) is not expected:
            raise ReconcileError(
                f"Shelfarr Audiobookshelf integration permission drifted: {key}"
            )
    if permissions.get("librariesAccessible") != [library_id]:
        raise ReconcileError(
            "Shelfarr Audiobookshelf integration library scope drifted"
        )


def validate_library(library: dict[str, Any]) -> None:
    settings = library.get("settings", {})
    expected = {
        "disableWatcher": True,
        "autoScanCronExpression": EXPECTED_SCAN_CRON,
        "audiobooksOnly": True,
    }
    for key, value in expected.items():
        if settings.get(key) != value:
            raise ReconcileError(f"Audiobookshelf library setting drifted: {key}")
    precedence = settings.get("metadataPrecedence", [])
    if not precedence or precedence[0] != "folderStructure":
        raise ReconcileError(
            "Audiobookshelf folder structure is not first in metadata precedence"
        )


def valid_scoped_key(
    base_url: str, token: str, expected_library_id: str
) -> bool:
    if not token:
        return False
    try:
        library, libraries = select_audiobook_library(base_url, token)
    except ReconcileError:
        return False
    return (
        library.get("id") == expected_library_id
        and len(libraries) == 1
        and library.get("folders", [{}])[0].get("fullPath")
        == EXPECTED_LIBRARY_PATH
    )


def reconcile(args: argparse.Namespace) -> None:
    env_lines = (
        args.env_file.read_text(encoding="utf-8").splitlines()
        if args.env_file.exists()
        else []
    )
    env_values = parse_values(env_lines)
    admin_token = root_token(args.ctid, args.container)
    library, _ = select_audiobook_library(args.base_url, admin_token)
    library_id = str(library["id"])

    if args.check:
        validate_library(library)
    else:
        api_request(
            args.base_url,
            admin_token,
            "PATCH",
            f"/api/libraries/{library_id}",
            {
                "settings": {
                    "disableWatcher": True,
                    "autoScanCronExpression": EXPECTED_SCAN_CRON,
                    "audiobooksOnly": True,
                    "metadataPrecedence": [
                        "folderStructure",
                        "audioMetatags",
                        "nfoFile",
                        "txtFiles",
                        "opfFile",
                        "absMetadata",
                    ],
                }
            },
        )
        library, _ = select_audiobook_library(args.base_url, admin_token)
        validate_library(library)

    users = api_request(args.base_url, admin_token, "GET", "/api/users").get(
        "users", []
    )
    matching_users = [
        user for user in users if user.get("username") == INTEGRATION_USERNAME
    ]
    if len(matching_users) > 1:
        raise ReconcileError("Multiple Shelfarr Audiobookshelf users exist")
    if matching_users:
        user = matching_users[0]
        if not args.check:
            response = api_request(
                args.base_url,
                admin_token,
                "PATCH",
                f"/api/users/{user['id']}",
                expected_user_payload(library_id),
            )
            user = response.get("user", {})
    elif args.check:
        raise ReconcileError("Shelfarr Audiobookshelf integration user is missing")
    else:
        password_alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(password_alphabet) for _ in range(48))
        response = api_request(
            args.base_url,
            admin_token,
            "POST",
            "/api/users",
            {
                "username": INTEGRATION_USERNAME,
                "password": password,
                **expected_user_payload(library_id),
            },
        )
        user = response.get("user", {})
    validate_user(user, library_id)

    existing_key = env_values.get(ENV_KEY, "")
    if not valid_scoped_key(args.base_url, existing_key, library_id):
        if args.check:
            raise ReconcileError(
                f"{ENV_KEY} is missing, inactive, or not scoped to the audiobook library"
            )
        response = api_request(
            args.base_url,
            admin_token,
            "POST",
            "/api/api-keys",
            {
                "name": API_KEY_NAME,
                "userId": user["id"],
                "isActive": True,
            },
        )
        generated_key = response.get("apiKey", {}).get("apiKey", "")
        if not generated_key or not valid_scoped_key(
            args.base_url, generated_key, library_id
        ):
            raise ReconcileError(
                "Audiobookshelf returned an invalid scoped API credential"
            )
        update_env(args.env_file, generated_key)
        existing_key = generated_key
    else:
        os.chmod(args.env_file, 0o600)

    api_keys = api_request(
        args.base_url, admin_token, "GET", "/api/api-keys"
    ).get("apiKeys", [])
    active_keys = [
        key
        for key in api_keys
        if key.get("name") == API_KEY_NAME
        and key.get("isActive")
        and (
            key.get("userId") == user["id"]
            or key.get("user", {}).get("id") == user["id"]
        )
    ]
    if not active_keys:
        raise ReconcileError("Shelfarr Audiobookshelf API key record is missing")
    if not valid_scoped_key(args.base_url, existing_key, library_id):
        raise ReconcileError("Shelfarr Audiobookshelf API key validation failed")

    action = "verified" if args.check else "reconciled"
    print(
        "Shelfarr Audiobookshelf integration "
        f"{action}; library_scope=1 api_key_active=true token_output=none"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path("/root/.env"))
    parser.add_argument("--ctid", type=int, default=112)
    parser.add_argument("--container", default="audiobookshelf")
    parser.add_argument(
        "--base-url", default="http://192.168.0.112:13378"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        reconcile(args)
    except (OSError, ReconcileError, KeyError, TypeError, ValueError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
