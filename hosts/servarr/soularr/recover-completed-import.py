#!/usr/bin/env python3
"""Trigger Lidarr's supported scan for a retained completed Soularr folder."""

from __future__ import annotations

import argparse
import copy
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import PurePosixPath

ALLOWED_ROOT = PurePosixPath("/data/media/slskd/complete")


def request(
    base_url: str,
    api_key: str,
    method: str,
    endpoint: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json", "X-Api-Key": api_key}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}{endpoint}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            decoded = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"Lidarr {method} {endpoint} returned HTTP {error.code}"
        ) from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"Lidarr {method} {endpoint} is unavailable") from error
    if not isinstance(decoded, dict):
        raise RuntimeError(f"Lidarr {method} {endpoint} returned invalid JSON")
    return decoded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--base-url", default="http://192.168.0.102:8686")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--album-id", type=int)
    parser.add_argument("--release-id", type=int)
    args = parser.parse_args()

    path = PurePosixPath(args.path)
    if not path.is_absolute() or path == ALLOWED_ROOT:
        raise RuntimeError("recovery path must be a folder below the completed root")
    if ".." in path.parts or not path.is_relative_to(ALLOWED_ROOT):
        raise RuntimeError("recovery path escapes the completed Soularr root")
    api_key = os.environ.get("LIDARR_API_KEY", "")
    if len(api_key) < 16:
        raise RuntimeError("LIDARR_API_KEY is missing")

    if (args.album_id is None) != (args.release_id is None):
        raise RuntimeError("--album-id and --release-id must be used together")

    original_album: dict[str, object] | None = None
    release_changed = False
    try:
        if args.album_id is not None and args.release_id is not None:
            original_album = request(
                args.base_url,
                api_key,
                "GET",
                f"/api/v1/album/{args.album_id}",
            )
            updated_album = copy.deepcopy(original_album)
            releases = updated_album.get("releases")
            if not isinstance(releases, list):
                raise RuntimeError("Lidarr album returned an invalid release list")
            targets = [
                release
                for release in releases
                if isinstance(release, dict)
                and int(release.get("id", 0)) == args.release_id
            ]
            if len(targets) != 1:
                raise RuntimeError("requested Lidarr release does not belong to album")
            for release in releases:
                if isinstance(release, dict):
                    release["monitored"] = int(release.get("id", 0)) == args.release_id
            request(
                args.base_url,
                api_key,
                "PUT",
                f"/api/v1/album/{args.album_id}",
                updated_album,
            )
            release_changed = True
            print(
                "Lidarr recovery release selected: "
                f"album_id={args.album_id} release_id={args.release_id}"
            )

        command = request(
            args.base_url,
            api_key,
            "POST",
            "/api/v1/command",
            {"name": "DownloadedAlbumsScan", "path": str(path)},
        )
        command_id = int(command["id"])
        print(f"Lidarr recovery scan accepted: command_id={command_id}")

        deadline = time.monotonic() + args.timeout_seconds
        while time.monotonic() < deadline:
            current = request(
                args.base_url,
                api_key,
                "GET",
                f"/api/v1/command/{command_id}",
            )
            status = str(current.get("status", "")).lower()
            if status in {"completed", "failed"}:
                message = str(current.get("message", ""))
                failed = status == "failed" or "failed" in message.lower()
                print(
                    "Lidarr recovery scan finished: "
                    f"status={status} imported={str(not failed).lower()}"
                )
                if failed:
                    raise RuntimeError("Lidarr reported that the recovery import failed")
                return 0
            time.sleep(2)
        raise RuntimeError("Lidarr recovery scan did not finish before its timeout")
    except Exception:
        if release_changed and original_album is not None and args.album_id is not None:
            request(
                args.base_url,
                api_key,
                "PUT",
                f"/api/v1/album/{args.album_id}",
                original_album,
            )
            print(f"Lidarr recovery release rolled back: album_id={args.album_id}")
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        raise SystemExit(1)
