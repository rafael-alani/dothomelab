#!/usr/bin/env python3
"""Canonicalize tags and art without taking ownership of music paths."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

CONFIG_ROOT = Path("/config")
MUSIC_ROOT = Path("/music")
LIDARR_ROOT = Path("/data/media/music")
SOULARR_LOCK = Path("/soularr-state/.dothomelab-job.lock")
WORKER_LOCK = CONFIG_ROOT / ".worker.lock"
STATE_PATH = CONFIG_ROOT / "state.json"
HEALTH_PATH = CONFIG_ROOT / "health.json"
REPORTS = CONFIG_ROOT / "reports"
WORK = CONFIG_ROOT / "work"
CONFIG = os.environ.get(
    "MUSIC_METADATA_BEETS_CONFIG", "/opt/dothomelab/config.yaml"
)
LIDARR_URL = os.environ.get("LIDARR_URL", "http://192.168.0.102:8686").rstrip("/")
LIDARR_KEY = os.environ.get("LIDARR_API_KEY", "")
POLL_SECONDS = int(os.environ.get("MUSIC_METADATA_POLL_SECONDS", "300"))
IMPORT_GRACE_SECONDS = int(
    os.environ.get("MUSIC_METADATA_IMPORT_GRACE_SECONDS", "600")
)
AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".alac",
    ".ape",
    ".dsf",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"history_cursor": 0, "pending_album_ids": []}
    with STATE_PATH.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise RuntimeError("state.json is not an object")
    return payload


def touch_health(*, status: str, detail: str = "") -> None:
    atomic_json(
        HEALTH_PATH,
        {
            "status": status,
            "detail": detail,
            "timestamp": int(time.time()),
        },
    )


class Lidarr:
    def __init__(self) -> None:
        if len(LIDARR_KEY) < 16:
            raise RuntimeError("LIDARR_API_KEY is missing or implausibly short")

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: object | None = None,
    ) -> Any:
        data = None
        headers = {"Accept": "application/json", "X-Api-Key": LIDARR_KEY}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{LIDARR_URL}/api/v1{path}",
            data=data,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise RuntimeError(
                f"Lidarr {method} {path} returned HTTP {error.code}: {detail}"
            ) from error
        return json.loads(body) if body else {}

    def album(self, album_id: int) -> dict[str, Any]:
        payload = self.request(f"/album/{album_id}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Lidarr album {album_id} is not an object")
        return payload

    def artist_files(self, artist_id: int) -> list[dict[str, Any]]:
        payload = self.request(f"/trackfile?artistId={artist_id}")
        if not isinstance(payload, list):
            raise RuntimeError(f"Lidarr track files for artist {artist_id} are invalid")
        return [item for item in payload if isinstance(item, dict)]

    def albums_with_files(self) -> list[int]:
        artists = self.artists_with_files()
        album_ids: set[int] = set()
        for artist in artists:
            artist_id = int(artist["id"])
            album_ids.update(
                int(item["albumId"])
                for item in self.artist_files(artist_id)
                if item.get("albumId") is not None
            )
        return sorted(album_ids)

    def artists_with_files(self) -> list[dict[str, Any]]:
        artists = self.request("/artist")
        if not isinstance(artists, list):
            raise RuntimeError("Lidarr artist response is invalid")
        return [
            artist
            for artist in artists
            if isinstance(artist, dict)
            and int((artist.get("statistics") or {}).get("trackFileCount") or 0) > 0
        ]

    def queue_is_idle(self) -> bool:
        payload = self.request("/queue?page=1&pageSize=100")
        records = payload.get("records", []) if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            raise RuntimeError("Lidarr queue response is invalid")
        return not any(
            str(item.get("status") or "").lower() not in {"", "completed"}
            for item in records
            if isinstance(item, dict)
        )

    def organize_preview(self, artist_id: int) -> list[dict[str, Any]]:
        payload = self.request(f"/rename?artistId={artist_id}")
        if not isinstance(payload, list):
            raise RuntimeError(f"Lidarr rename preview for artist {artist_id} is invalid")
        return [item for item in payload if isinstance(item, dict)]

    def wait_command(self, command_id: int, timeout: int = 1800) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            payload = self.request(f"/command/{command_id}")
            status = str(payload.get("status") or "").lower()
            if status == "completed":
                return payload
            if status in {"failed", "aborted"}:
                raise RuntimeError(
                    f"Lidarr command {command_id} ended as {status}: "
                    f"{payload.get('message') or payload.get('errorMessage') or ''}"
                )
            time.sleep(2)
        raise RuntimeError(f"Lidarr command {command_id} timed out")

    def imported_history(self) -> tuple[int, set[int]]:
        query = urllib.parse.urlencode(
            {
                "page": 1,
                "pageSize": 1000,
                "sortKey": "date",
                "sortDirection": "descending",
            }
        )
        payload = self.request(f"/history?{query}")
        records = payload.get("records", []) if isinstance(payload, dict) else []
        cursor = 0
        albums: set[int] = set()
        state_cursor = int(load_state().get("history_cursor") or 0)
        for item in records:
            if not isinstance(item, dict):
                continue
            record_id = int(item.get("id") or 0)
            cursor = max(cursor, record_id)
            if (
                record_id > state_cursor
                and item.get("eventType") == "trackFileImported"
                and item.get("albumId") is not None
            ):
                albums.add(int(item["albumId"]))
        return cursor, albums


@contextlib.contextmanager
def exclusive_lock(path: Path, *, blocking: bool = True) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(handle, flags)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def local_path(lidarr_path: str) -> Path:
    source = Path(lidarr_path)
    try:
        relative = source.relative_to(LIDARR_ROOT)
    except ValueError as error:
        raise RuntimeError(f"Lidarr path escapes its music root: {source}") from error
    target = MUSIC_ROOT / relative
    resolved_parent = target.parent.resolve(strict=True)
    try:
        resolved_parent.relative_to(MUSIC_ROOT.resolve(strict=True))
    except ValueError as error:
        raise RuntimeError(f"music path resolves outside /music: {target}") from error
    return resolved_parent / target.name


def selected_release(album: dict[str, Any]) -> str:
    releases = [
        item
        for item in album.get("releases", [])
        if isinstance(item, dict) and item.get("monitored") is True
    ]
    if len(releases) != 1:
        raise RuntimeError(
            f"album {album.get('id')} has {len(releases)} selected releases; expected one"
        )
    release_id = str(releases[0].get("foreignReleaseId") or "")
    if len(release_id) != 36:
        raise RuntimeError(f"album {album.get('id')} has no valid MusicBrainz release ID")
    return release_id


def audio_paths_below(root: Path) -> set[Path]:
    return {
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    }


def detach_hardlink(path: Path) -> bool:
    metadata = path.stat()
    if metadata.st_nlink <= 1:
        return False
    temporary = path.with_name(f".{path.name}.detach-{os.getpid()}-{time.time_ns()}")
    try:
        copy_command = [
            "cp",
            "--reflink=always",
            "--preserve=mode,timestamps,xattr",
            "--",
            str(path),
            str(temporary),
        ]
        cloned = subprocess.run(
            copy_command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
        if cloned.returncode != 0:
            with contextlib.suppress(FileNotFoundError):
                temporary.unlink()
            copy_command[1] = "--reflink=auto"
            subprocess.run(copy_command, check=True, timeout=1800)
        copied = temporary.stat()
        if copied.st_size != metadata.st_size or copied.st_nlink != 1:
            raise RuntimeError(f"independent-copy detach verification failed for {path}")
        subprocess.run(
            ["cmp", "-s", "--", str(path), str(temporary)],
            check=True,
            timeout=1800,
        )
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if path.stat().st_nlink != 1:
            raise RuntimeError(f"hardlink detach did not produce an independent file: {path}")
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
    return True


def run_beets(album_id: int, release_id: str, album_root: Path) -> tuple[int, str]:
    database = WORK / f"album-{album_id}.db"
    log = WORK / f"album-{album_id}.log"
    for stale in (database, Path(f"{database}.bak"), log):
        with contextlib.suppress(FileNotFoundError):
            stale.unlink()
    command = [
        "beet",
        "--config",
        CONFIG,
        "--library",
        str(database),
        "import",
        "-C",
        "-M",
        "-q",
        "-P",
        "--flat",
        "--search-id",
        release_id,
        "-l",
        str(log),
        str(album_root),
    ]
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=7200,
    )
    output = completed.stdout[-12000:]
    if completed.returncode != 0:
        raise RuntimeError(
            f"beets failed for album {album_id} with {completed.returncode}: {output}"
        )
    listed = subprocess.run(
        [
            "beet",
            "--config",
            CONFIG,
            "--library",
            str(database),
            "list",
            "-f",
            "$path",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    count = len([line for line in listed.stdout.splitlines() if line.strip()])
    return count, output


def process_album(api: Lidarr, album_id: int) -> dict[str, Any]:
    started = int(time.time())
    report: dict[str, Any] = {"album_id": album_id, "started": started}
    try:
        album = api.album(album_id)
        artist_id = int(album["artistId"])
        artist_files = api.artist_files(artist_id)
        records = [
            item for item in artist_files if int(item.get("albumId") or 0) == album_id
        ]
        if not records:
            return report | {"status": "no_files", "finished": int(time.time())}
        paths = [local_path(str(item["path"])) for item in records]
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise RuntimeError(f"{len(missing)} Lidarr paths are missing below /music")
        newest = max(path.stat().st_mtime for path in paths)
        if time.time() - newest < IMPORT_GRACE_SECONDS:
            return report | {
                "status": "deferred",
                "reason": "import grace period",
                "finished": int(time.time()),
            }
        common = Path(os.path.commonpath([str(path.parent) for path in paths]))
        if common == MUSIC_ROOT or common.parent == MUSIC_ROOT:
            return report | {
                "status": "needs_organize",
                "reason": f"album files are not isolated below one album directory: {common}",
                "finished": int(time.time()),
            }
        mixed = [
            item
            for item in artist_files
            if int(item.get("albumId") or 0) != album_id
            and local_path(str(item["path"])).is_relative_to(common)
        ]
        if mixed:
            return report | {
                "status": "needs_organize",
                "reason": f"album directory also contains {len(mixed)} other Lidarr files",
                "finished": int(time.time()),
            }
        release_id = selected_release(album)
        before = audio_paths_below(common)
        expected = set(paths)
        if before != expected:
            return report | {
                "status": "needs_review",
                "reason": (
                    f"album directory has {len(before)} audio files but Lidarr owns "
                    f"{len(expected)}"
                ),
                "finished": int(time.time()),
            }
        with exclusive_lock(SOULARR_LOCK):
            detached = sum(detach_hardlink(path) for path in paths)
            imported, beets_output = run_beets(album_id, release_id, common)
        after = audio_paths_below(common)
        if after != before:
            raise RuntimeError("beets changed the album's audio path set")
        if imported != len(paths):
            return report | {
                "status": "unmatched",
                "release_id": release_id,
                "files": len(paths),
                "beets_items": imported,
                "detached_hardlinks": detached,
                "beets_tail": beets_output,
                "finished": int(time.time()),
            }
        art = common / "cover.jpg"
        return report | {
            "status": "tagged" if art.is_file() else "tagged_missing_art",
            "release_id": release_id,
            "files": len(paths),
            "beets_items": imported,
            "detached_hardlinks": detached,
            "album_root": str(common),
            "cover": str(art) if art.is_file() else None,
            "finished": int(time.time()),
        }
    except Exception as error:
        return report | {
            "status": "failed",
            "error": f"{type(error).__name__}: {error}",
            "finished": int(time.time()),
        }


def write_report(report: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    day = time.strftime("%Y-%m-%d", time.gmtime())
    with (REPORTS / f"reconcile-{day}.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(report, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(report, sort_keys=True), flush=True)


def organize_existing(api: Lidarr) -> int:
    summary: list[dict[str, Any]] = []
    with exclusive_lock(WORKER_LOCK), exclusive_lock(SOULARR_LOCK):
        if not api.queue_is_idle():
            raise RuntimeError("Lidarr queue is not idle; refusing to organize")
        for artist in api.artists_with_files():
            artist_id = int(artist["id"])
            preview = api.organize_preview(artist_id)
            if not preview:
                continue
            file_ids = [int(item["trackFileId"]) for item in preview]
            command = api.request(
                "/command",
                method="POST",
                payload={
                    "name": "RenameFiles",
                    "artistId": artist_id,
                    "files": file_ids,
                },
            )
            command_id = int(command["id"])
            api.wait_command(command_id)
            remaining = api.organize_preview(artist_id)
            if remaining:
                raise RuntimeError(
                    f"Lidarr left {len(remaining)} rename actions for artist {artist_id}"
                )
            item = {
                "artist_id": artist_id,
                "artist": artist.get("artistName"),
                "files": len(file_ids),
                "command_id": command_id,
            }
            summary.append(item)
            print(json.dumps(item, sort_keys=True), flush=True)
    report = {
        "status": "organized",
        "artists": len(summary),
        "files": sum(item["files"] for item in summary),
        "details": summary,
        "finished": int(time.time()),
    }
    atomic_json(REPORTS / "lidarr-organize.json", report)
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0


def reconcile(api: Lidarr, album_ids: list[int]) -> int:
    failures = 0
    with exclusive_lock(WORKER_LOCK):
        for album_id in album_ids:
            touch_health(status="working", detail=f"album {album_id}")
            report = process_album(api, album_id)
            write_report(report)
            if report["status"] not in {"tagged", "tagged_missing_art", "no_files"}:
                failures += 1
        touch_health(
            status="ok",
            detail=f"reconciled {len(album_ids)} albums with {failures} exceptions",
        )
    return 0 if failures == 0 else 2


def daemon() -> int:
    api = Lidarr()
    touch_health(status="starting", detail="initial Lidarr history poll")
    while True:
        try:
            with exclusive_lock(WORKER_LOCK):
                state = load_state()
                cursor, imported = api.imported_history()
                pending = {
                    int(value) for value in state.get("pending_album_ids", [])
                } | imported
                retained: set[int] = set()
                for album_id in sorted(pending):
                    touch_health(status="working", detail=f"album {album_id}")
                    report = process_album(api, album_id)
                    write_report(report)
                    if report["status"] in {
                        "deferred",
                        "failed",
                        "needs_organize",
                        "needs_review",
                        "unmatched",
                    }:
                        retained.add(album_id)
                atomic_json(
                    STATE_PATH,
                    {
                        "history_cursor": max(
                            int(state.get("history_cursor") or 0), cursor
                        ),
                        "pending_album_ids": sorted(retained),
                        "last_poll": int(time.time()),
                    },
                )
                touch_health(
                    status="ok",
                    detail=f"{len(retained)} albums pending",
                )
        except Exception as error:
            touch_health(status="error", detail=f"{type(error).__name__}: {error}")
            print(f"music metadata poll failed: {type(error).__name__}: {error}", flush=True)
        time.sleep(POLL_SECONDS)


def healthcheck() -> int:
    try:
        with HEALTH_PATH.open(encoding="utf-8") as stream:
            health = json.load(stream)
        age = time.time() - int(health["timestamp"])
        if age > POLL_SECONDS * 2 + 180:
            raise RuntimeError(f"worker health is stale by {int(age)} seconds")
        if health.get("status") == "error":
            raise RuntimeError(str(health.get("detail") or "worker error"))
    except Exception as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def check() -> int:
    api = Lidarr()
    checks: dict[str, Any] = {
        "lidarr_status": api.request("/system/status").get("version"),
        "music_root": str(MUSIC_ROOT.resolve(strict=True)),
        "music_writable": os.access(MUSIC_ROOT, os.R_OK | os.W_OK),
        "soularr_lock": str(SOULARR_LOCK.resolve(strict=True)),
        "beets": subprocess.run(
            ["beet", "--version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            timeout=30,
        ).stdout.strip(),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "cp": bool(shutil.which("cp")),
    }
    naming = api.request("/config/naming")
    media = api.request("/config/mediamanagement")
    provider = api.request("/config/metadataprovider")
    checks["lidarr_policy"] = {
        "rename_tracks": naming.get("renameTracks"),
        "copy_using_hardlinks": media.get("copyUsingHardlinks"),
        "write_audio_tags": provider.get("writeAudioTags"),
        "embed_cover_art": provider.get("embedCoverArt"),
    }
    expected = {
        "rename_tracks": True,
        "copy_using_hardlinks": False,
        "write_audio_tags": "no",
        "embed_cover_art": False,
    }
    if checks["lidarr_policy"] != expected:
        raise RuntimeError(f"Lidarr music policy drift: {checks['lidarr_policy']}")
    if not all((checks["music_writable"], checks["ffmpeg"], checks["cp"])):
        raise RuntimeError(f"runtime capability check failed: {checks}")
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "daemon"
    if command == "daemon":
        return daemon()
    if command == "healthcheck":
        return healthcheck()
    if command == "check":
        return check()
    if command == "reconcile":
        api = Lidarr()
        album_ids = (
            [int(value) for value in sys.argv[2:]]
            if len(sys.argv) > 2
            else api.albums_with_files()
        )
        return reconcile(api, album_ids)
    if command == "organize":
        return organize_existing(Lidarr())
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
