#!/usr/bin/env python3
"""Make Lidarr the path authority and disable its lower-fidelity tag writer."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = "http://192.168.0.102:8686/api/v1"
KEY = os.environ.get("LIDARR_API_KEY", "")


def request(
    path: str, *, method: str = "GET", payload: object | None = None
) -> dict[str, object]:
    if len(KEY) < 16:
        raise RuntimeError("LIDARR_API_KEY is missing or implausibly short")
    data = None
    headers = {"Accept": "application/json", "X-Api-Key": KEY}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Lidarr {method} {path} returned HTTP {error.code}: {detail}"
        ) from error
    result = json.loads(body) if body else {}
    if not isinstance(result, dict):
        raise RuntimeError(f"Lidarr {path} did not return an object")
    return result


def reconcile(path: str, expected: dict[str, object]) -> None:
    current = request(path)
    changed = False
    for key, value in expected.items():
        if current.get(key) != value:
            current[key] = value
            changed = True
    if changed:
        request(path, method="PUT", payload=current)
    actual = request(path)
    drift = {
        key: actual.get(key)
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if drift:
        raise RuntimeError(f"Lidarr {path} policy drift: {drift}")


def main() -> int:
    reconcile(
        "/config/naming",
        {
            "renameTracks": True,
            "standardTrackFormat": (
                "{Album Title} ({Release Year})/"
                "{Artist Name} - {Album Title} - {track:00} - {Track Title}"
            ),
            "multiDiscTrackFormat": (
                "{Album Title} ({Release Year})/{Medium Format} {medium:00}/"
                "{Artist Name} - {Album Title} - {track:00} - {Track Title}"
            ),
            "artistFolderFormat": "{Artist Name}",
        },
    )
    reconcile(
        "/config/mediamanagement",
        {
            "copyUsingHardlinks": False,
            "importExtraFiles": False,
            "watchLibraryForChanges": True,
            "rescanAfterRefresh": "always",
            "allowFingerprinting": "newFiles",
        },
    )
    reconcile(
        "/config/metadataprovider",
        {
            "writeAudioTags": "no",
            "scrubAudioTags": False,
            "embedCoverArt": False,
        },
    )
    print(
        "Lidarr music policy verified: path authority enabled, hardlink imports "
        "disabled, metadata writes delegated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
