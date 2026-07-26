#!/usr/bin/env python3
"""Trigger Lidarr's supported scan for a retained completed Soularr folder."""

from __future__ import annotations

import argparse
import copy
import json
import os
import time
import urllib.error
import urllib.parse
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


def request_list(
    base_url: str,
    api_key: str,
    method: str,
    endpoint: str,
    payload: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
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
        with urllib.request.urlopen(req, timeout=120) as response:
            decoded = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"Lidarr {method} {endpoint.split('?', 1)[0]} returned HTTP {error.code}"
        ) from None
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Lidarr {method} {endpoint.split('?', 1)[0]} is unavailable"
        ) from error
    if not isinstance(decoded, list) or not all(
        isinstance(item, dict) for item in decoded
    ):
        raise RuntimeError(
            f"Lidarr {method} {endpoint.split('?', 1)[0]} returned invalid JSON"
        )
    return decoded


def manual_import(
    base_url: str,
    api_key: str,
    path: PurePosixPath,
    album_id: int,
    release_id: int,
    timeout_seconds: int,
) -> None:
    query = urllib.parse.urlencode(
        {
            "folder": str(path),
            "filterExistingFiles": "true",
            "replaceExistingFiles": "false",
        }
    )
    items = request_list(
        base_url,
        api_key,
        "GET",
        f"/api/v1/manualimport?{query}",
    )
    if not items:
        raise RuntimeError("Lidarr manual analysis returned no files")
    for item in items:
        item_path = PurePosixPath(str(item.get("path", "")))
        album = item.get("album")
        tracks = item.get("tracks")
        rejections = item.get("rejections")
        if not item_path.is_relative_to(path):
            raise RuntimeError("Lidarr manual analysis returned a path outside the folder")
        if not isinstance(album, dict) or int(album.get("id", 0)) != album_id:
            raise RuntimeError("Lidarr manual analysis matched the wrong album")
        if not isinstance(tracks, list) or not tracks:
            raise RuntimeError("Lidarr manual analysis returned an unmatched track")
        if isinstance(rejections, list) and rejections:
            raise RuntimeError("Lidarr manual analysis returned a rejected file")
        item["albumReleaseId"] = release_id
        item["disableReleaseSwitching"] = True
        item["replaceExistingFiles"] = False
    analyzed = request_list(
        base_url,
        api_key,
        "POST",
        "/api/v1/manualimport",
        items,
    )
    if len(analyzed) != len(items):
        raise RuntimeError("Lidarr manual import returned an incomplete result")
    files: list[dict[str, object]] = []
    for item in analyzed:
        artist = item.get("artist")
        album = item.get("album")
        tracks = item.get("tracks")
        rejections = item.get("rejections")
        if (
            not isinstance(artist, dict)
            or not isinstance(album, dict)
            or not isinstance(tracks, list)
            or not tracks
        ):
            raise RuntimeError("Lidarr returned incomplete manual import analysis")
        if isinstance(rejections, list) and rejections:
            raise RuntimeError("Lidarr rejected a reviewed manual import file")
        files.append(
            {
                "path": item["path"],
                "artistId": int(artist["id"]),
                "albumId": int(album["id"]),
                "albumReleaseId": release_id,
                "trackIds": [int(track["id"]) for track in tracks],
                "quality": item["quality"],
                "indexerFlags": int(item.get("indexerFlags", 0)),
                "downloadId": item.get("downloadId"),
                "disableReleaseSwitching": True,
            }
        )
    command = request(
        base_url,
        api_key,
        "POST",
        "/api/v1/command",
        {
            "name": "ManualImport",
            "files": files,
            "importMode": "copy",
            "replaceExistingFiles": False,
        },
    )
    command_id = int(command["id"])
    print(
        "Lidarr supported manual recovery accepted: "
        f"command_id={command_id} files={len(files)} mode=copy"
    )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current = request(
            base_url,
            api_key,
            "GET",
            f"/api/v1/command/{command_id}",
        )
        status = str(current.get("status", "")).lower()
        if status in {"completed", "failed"}:
            message = str(current.get("message", ""))
            failed = status == "failed" or "failed" in message.lower()
            print(
                "Lidarr supported manual recovery finished: "
                f"status={status} imported={str(not failed).lower()}"
            )
            if failed:
                raise RuntimeError("Lidarr reported that manual recovery failed")
            return
        time.sleep(2)
    raise RuntimeError("Lidarr manual recovery did not finish before its timeout")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--base-url", default="http://192.168.0.102:8686")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--album-id", type=int)
    parser.add_argument("--release-id", type=int)
    parser.add_argument("--manual-on-scan-failure", action="store_true")
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
    if args.manual_on_scan_failure and args.album_id is None:
        raise RuntimeError(
            "--manual-on-scan-failure requires --album-id and --release-id"
        )

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
                    if args.manual_on_scan_failure:
                        manual_import(
                            args.base_url,
                            api_key,
                            path,
                            args.album_id,
                            args.release_id,
                            args.timeout_seconds,
                        )
                        return 0
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
