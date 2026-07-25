#!/usr/bin/env python3
"""Idempotently initialize BookOrbit and reconcile its read-only libraries."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE_URL = "http://192.168.0.112:3002/api/v1"
LIBRARIES = (
    ("Ebooks", "BookOpen", "/library/ebooks", ["epub", "kepub", "mobi", "azw3", "azw", "fb2"]),
    ("PDFs", "FileText", "/library/pdfs", ["pdf"]),
    ("Comics", "PanelsTopLeft", "/library/comics", ["cbz", "cbr", "cb7"]),
    ("Manga", "BookOpenText", "/library/mangas", ["cbz", "cbr", "cb7"]),
)


def request(
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    accepted_error_codes: tuple[int, ...] = (),
) -> object:
    data = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Accept": "application/json"}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        if error.code in accepted_error_codes:
            return json.loads(detail) if detail else {}
        raise RuntimeError(f"BookOrbit {method} {path} returned {error.code}: {detail[:500]}") from error
    return json.loads(body) if body else {}


def main() -> int:
    username = "rafael"
    password = os.environ["BOOKORBIT_ADMIN_PASSWORD"]
    status = request("/auth/setup-status")
    if status.get("needsSetup"):
        request(
            "/auth/setup",
            method="POST",
            payload={
                "username": username,
                "name": "Rafael",
                "email": "rafael@rafael.media",
                "password": password,
            },
            headers={"x-setup-token": os.environ["BOOKORBIT_SETUP_BOOTSTRAP_TOKEN"]},
        )

    login = request(
        "/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    token = login["accessToken"]
    existing = {item["name"]: item for item in request("/libraries", token=token)}

    for order, (name, icon, folder, formats) in enumerate(LIBRARIES):
        desired = {
            "name": name,
            "icon": icon,
            "displayOrder": order,
            "folders": [folder],
            "watch": True,
            "autoScanCronExpression": "0 4 * * *",
            "allowedFormats": formats,
            "organizationMode": "book_per_folder",
            "fileWriteEnabled": False,
            "fileWriteWriteCover": False,
            "fileWriteEpubEnabled": False,
            "fileWritePdfEnabled": False,
            "fileWriteCbxEnabled": False,
            "fileWriteAudioEnabled": False,
            "fileRenameEnabled": False,
        }
        if name in existing:
            library = request(
                f"/libraries/{existing[name]['id']}",
                method="PATCH",
                payload=desired,
                token=token,
            )
        else:
            library = request("/libraries", method="POST", payload=desired, token=token)
        request(
            f"/scanner/libraries/{library['id']}/scan",
            method="POST",
            token=token,
            accepted_error_codes=(409,),
        )

    opds_username = "rafael-opds"
    opds_users = request("/opds-users", token=token)
    if not any(item["username"] == opds_username for item in opds_users):
        request(
            "/opds-users",
            method="POST",
            payload={
                "username": opds_username,
                "password": os.environ["BOOKORBIT_OPDS_PASSWORD"],
                "sortOrder": "title_asc",
            },
            token=token,
        )

    print("BookOrbit administrator, four read-only libraries, scans, and OPDS user reconciled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
