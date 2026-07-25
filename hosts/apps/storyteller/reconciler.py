#!/usr/bin/env python3
"""Safely stage exact Shelfarr ebook/audiobook pairs for Storyteller."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

VERSION = 1
DEFAULT_EBOOK_ROOT = Path("/sources/ebooks")
DEFAULT_AUDIOBOOK_ROOT = Path("/sources/audiobooks")
DEFAULT_INBOX = Path("/storyteller/inbox")
DEFAULT_LIBRARY = Path("/storyteller/library")
DEFAULT_STATE = Path("/state")
DEFAULT_DATABASE = Path("/storyteller-db/storyteller.db")
SUPPORTED_AUDIO = {".m4b", ".m4a", ".mp4", ".mp3", ".zip"}
ACTIVE_STORYTELLER_STATES = {"QUEUED", "PROCESSING"}
GIB = 1024**3


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def emit(message: str) -> None:
    print(f"{now()} {message}", flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def safe_key(key: str) -> bool:
    parts = Path(key).parts
    if len(parts) != 2:
        return False
    for part in parts:
        if (
            not part
            or part in {".", ".."}
            or part.startswith(".")
            or part != part.strip()
            or "\\" in part
            or len(part.encode("utf-8")) > 180
            or any(ord(character) < 32 for character in part)
        ):
            return False
    return True


def is_regular_file(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return False
    return stat.S_ISREG(mode) and not path.is_symlink()


def source_file_record(path: Path) -> dict[str, Any]:
    if not is_regular_file(path):
        raise RuntimeError(f"source is not a regular non-symlink file: {path}")
    before = path.stat()
    digest = sha256_file(path)
    after = path.stat()
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after:
        raise RuntimeError(f"source changed while hashing: {path}")
    return {
        "path": str(path),
        "device": after.st_dev,
        "inode": after.st_ino,
        "size": after.st_size,
        "mtime_ns": after.st_mtime_ns,
        "sha256": digest,
    }


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        fsync_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": VERSION, "updated_at": now(), "items": {}}
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("version") != VERSION or not isinstance(
        manifest.get("items"), dict
    ):
        raise RuntimeError(f"unsupported manifest at {path}")
    return manifest


@contextlib.contextmanager
def operation_lock(state_root: Path, blocking: bool = False) -> Iterator[None]:
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "reconciler.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        try:
            fcntl.flock(handle, flags)
        except BlockingIOError as error:
            raise RuntimeError("another reconciler operation is active") from error
        yield


def iter_book_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    if not root.is_dir():
        return keys
    for author in root.iterdir():
        if not author.is_dir() or author.is_symlink():
            continue
        for title in author.iterdir():
            if title.is_dir() and not title.is_symlink():
                keys.add(f"{author.name}/{title.name}")
    return keys


def find_files(root: Path, suffixes: set[str]) -> list[Path]:
    found: list[Path] = []
    if not root.is_dir() or root.is_symlink():
        return found
    for candidate in root.rglob("*"):
        if (
            is_regular_file(candidate)
            and candidate.suffix.lower() in suffixes
            and not any(part.startswith(".") for part in candidate.relative_to(root).parts)
        ):
            found.append(candidate)
    return sorted(found, key=lambda path: str(path.relative_to(root)).casefold())


def pair_candidate(
    key: str, ebook_root: Path, audiobook_root: Path
) -> tuple[str, list[Path], list[Path], str | None]:
    if not safe_key(key):
        return key, [], [], "unsafe relative book key"
    ebook_dir = ebook_root / key
    audiobook_dir = audiobook_root / key
    epubs = find_files(ebook_dir, {".epub"})
    audio = find_files(audiobook_dir, SUPPORTED_AUDIO)
    if len(epubs) > 1:
        return key, epubs, audio, f"ambiguous ebook side: {len(epubs)} EPUB files"
    if len(epubs) == 0 and not audio:
        return key, epubs, audio, "no supported media"
    if len(epubs) == 0:
        return key, epubs, audio, "incomplete pair: EPUB side is missing"
    if not audio:
        return key, epubs, audio, "incomplete pair: audiobook side is missing"
    return key, epubs, audio, None


def source_fingerprint(
    ebook: list[dict[str, Any]], audio: list[dict[str, Any]]
) -> dict[str, Any]:
    return {"ebook": ebook, "audiobook": audio}


def identity_matches(
    fingerprint: dict[str, Any], epubs: list[Path], audio: list[Path]
) -> bool:
    for key, paths in (("ebook", epubs), ("audiobook", audio)):
        records = fingerprint.get(key)
        if not isinstance(records, list) or len(records) != len(paths):
            return False
        for record, path in zip(records, paths, strict=True):
            try:
                state = path.stat()
            except FileNotFoundError:
                return False
            if (
                not is_regular_file(path)
                or record.get("path") != str(path)
                or record.get("device") != state.st_dev
                or record.get("inode") != state.st_ino
                or record.get("size") != state.st_size
                or record.get("mtime_ns") != state.st_mtime_ns
            ):
                return False
    return True


def flattened_audio_name(path: Path, audiobook_dir: Path) -> str:
    relative = path.relative_to(audiobook_dir)
    return " - ".join(relative.parts)


def copy_verified(source: Path, destination: Path, expected_hash: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer, length=1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())
    os.chmod(destination, 0o640)
    actual = sha256_file(destination)
    if actual != expected_hash:
        raise RuntimeError(
            f"copy verification failed for {source}: expected {expected_hash}, got {actual}"
        )


def mark_consumed(manifest: dict[str, Any], inbox: Path) -> int:
    changed = 0
    for key, item in manifest["items"].items():
        if item.get("stage_state") != "published":
            continue
        if not (inbox / key).exists():
            item["stage_state"] = "inbox-consumed"
            item["storyteller_state"] = "imported-unverified"
            item["updated_at"] = now()
            changed += 1
    return changed


def update_error(
    manifest: dict[str, Any],
    key: str,
    reason: str,
    stage_state: str,
) -> None:
    existing = manifest["items"].get(key, {})
    manifest["items"][key] = {
        **existing,
        "key": key,
        "stage_state": stage_state,
        "storyteller_state": existing.get("storyteller_state", "not-imported"),
        "attempts": int(existing.get("attempts", 0)) + 1,
        "last_error": reason,
        "updated_at": now(),
    }


def reconcile(args: argparse.Namespace, dry_run: bool) -> dict[str, int]:
    ebook_root = Path(args.ebook_root)
    audiobook_root = Path(args.audiobook_root)
    inbox = Path(args.inbox)
    state_root = Path(args.state_root)
    manifest_path = state_root / "manifest.json"
    update_marker = state_root / "wud-update.lock"
    summary: Counter[str] = Counter()

    if update_marker.exists():
        raise RuntimeError("WUD update guard is active")

    with operation_lock(state_root):
        if update_marker.exists():
            raise RuntimeError("WUD update guard became active")
        manifest = load_manifest(manifest_path)
        if mark_consumed(manifest, inbox):
            summary["inbox_consumed"] += 1

        keys = sorted(iter_book_keys(ebook_root) | iter_book_keys(audiobook_root))
        candidates: list[tuple[str, list[Path], list[Path]]] = []
        for key in keys:
            key, epubs, audio, error = pair_candidate(
                key, ebook_root, audiobook_root
            )
            if error:
                summary["skipped"] += 1
                emit(f"SKIP key={json.dumps(key)} reason={json.dumps(error)}")
                if not dry_run:
                    state = "ambiguous" if "ambiguous" in error else "incomplete"
                    update_error(manifest, key, error, state)
                continue
            candidates.append((key, epubs, audio))

        staged_this_run = 0
        for key, epubs, audio in candidates:
            final = inbox / key
            existing = manifest["items"].get(key, {})
            try:
                if (
                    existing.get("stage_state")
                    in {"published", "inbox-consumed", "imported", "aligned"}
                    and isinstance(existing.get("sources"), dict)
                    and identity_matches(existing["sources"], epubs, audio)
                ):
                    summary["unchanged"] += 1
                    emit(f"UNCHANGED key={json.dumps(key)}")
                    continue
                if staged_this_run >= args.max_items:
                    summary["deferred"] += 1
                    emit(f"DEFERRED key={json.dumps(key)}")
                    continue

                ebook_records = [source_file_record(path) for path in epubs]
                audio_records = [source_file_record(path) for path in audio]
                fingerprint = source_fingerprint(ebook_records, audio_records)

                if existing.get("sources") == fingerprint and existing.get(
                    "stage_state"
                ) in {"published", "inbox-consumed", "imported", "aligned"}:
                    summary["unchanged"] += 1
                    emit(f"UNCHANGED key={json.dumps(key)}")
                    continue
                if existing.get("sources") and existing.get("sources") != fingerprint:
                    reason = "canonical source identity changed after first staging"
                    summary["changed"] += 1
                    emit(f"SKIP key={json.dumps(key)} reason={json.dumps(reason)}")
                    if not dry_run:
                        update_error(manifest, key, reason, "changed-source")
                    continue
                if final.exists():
                    reason = "Storyteller inbox destination already exists"
                    summary["conflict"] += 1
                    emit(f"SKIP key={json.dumps(key)} reason={json.dumps(reason)}")
                    if not dry_run:
                        update_error(manifest, key, reason, "conflict")
                    continue

                total_size = sum(
                    record["size"] for record in ebook_records + audio_records
                )
                free = shutil.disk_usage(inbox).free
                required = max(
                    int(args.min_free_gib * GIB),
                    total_size * 2 + int(args.copy_headroom_gib * GIB),
                )
                if free < required:
                    reason = (
                        f"low free space: free={free} required={required} "
                        f"pair_bytes={total_size}"
                    )
                    summary["low_space"] += 1
                    emit(f"SKIP key={json.dumps(key)} reason={json.dumps(reason)}")
                    if not dry_run:
                        update_error(manifest, key, reason, "low-space")
                    continue

                if dry_run:
                    staged_this_run += 1
                    summary["would_stage"] += 1
                    emit(
                        f"WOULD-STAGE key={json.dumps(key)} "
                        f"files={len(epubs) + len(audio)} bytes={total_size}"
                    )
                    continue

                # Keep partial copies outside the watched inbox. Both paths
                # remain on the same filesystem, so the final rename is atomic.
                staging_root = inbox.parent / ".staging"
                staging_root.mkdir(parents=True, exist_ok=True)
                os.chmod(staging_root, 0o750)
                temporary = staging_root / (
                    hashlib.sha256(key.encode()).hexdigest()[:16]
                    + "-"
                    + uuid.uuid4().hex
                )
                temporary.mkdir(mode=0o750)
                try:
                    epub_name = epubs[0].name
                    audio_names = [
                        flattened_audio_name(path, audiobook_root / key)
                        for path in audio
                    ]
                    staged_names = [epub_name, *audio_names]
                    if len(staged_names) != len(set(staged_names)):
                        raise RuntimeError(
                            "flattened staged filenames would collide"
                        )
                    copy_verified(
                        epubs[0], temporary / epub_name, ebook_records[0]["sha256"]
                    )
                    for source, record, destination_name in zip(
                        audio, audio_records, audio_names, strict=True
                    ):
                        copy_verified(
                            source, temporary / destination_name, record["sha256"]
                        )
                    fsync_directory(temporary)
                    final.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(temporary, final)
                    fsync_directory(final.parent)
                finally:
                    if temporary.exists():
                        shutil.rmtree(temporary)

                manifest["items"][key] = {
                    "key": key,
                    "sources": fingerprint,
                    "staged_files": staged_names,
                    "staged_bytes": total_size,
                    "stage_state": "published",
                    "storyteller_state": "awaiting-import",
                    "attempts": int(existing.get("attempts", 0)) + 1,
                    "last_error": None,
                    "published_at": now(),
                    "updated_at": now(),
                }
                staged_this_run += 1
                summary["staged"] += 1
                emit(
                    f"STAGED key={json.dumps(key)} files={len(staged_names)} "
                    f"bytes={total_size}"
                )
            except Exception as error:
                summary["errors"] += 1
                emit(f"ERROR key={json.dumps(key)} detail={json.dumps(str(error))}")
                if not dry_run:
                    update_error(manifest, key, str(error), "error")

        if not dry_run:
            manifest["updated_at"] = now()
            atomic_json_write(manifest_path, manifest)
        emit(
            "SUMMARY "
            + " ".join(f"{key}={value}" for key, value in sorted(summary.items()))
        )
    return dict(summary)


def storyteller_active_jobs(database: Path) -> int:
    if not database.is_file():
        return 0
    connection = sqlite3.connect(
        f"file:{database}?mode=ro", uri=True, timeout=5
    )
    try:
        table = connection.execute(
            "SELECT count(*) FROM sqlite_master "
            "WHERE type='table' AND name='readaloud'"
        ).fetchone()[0]
        if not table:
            return 0
        placeholders = ",".join("?" for _ in ACTIVE_STORYTELLER_STATES)
        return int(
            connection.execute(
                f"SELECT count(*) FROM readaloud WHERE status IN ({placeholders})",
                sorted(ACTIVE_STORYTELLER_STATES),
            ).fetchone()[0]
        )
    finally:
        connection.close()


def inbox_has_work(inbox: Path) -> bool:
    if not inbox.is_dir():
        return False
    for path in inbox.rglob("*"):
        if ".staging" in path.parts:
            continue
        if path.is_file():
            return True
    return False


def busy_reasons(args: argparse.Namespace, include_marker: bool = True) -> list[str]:
    reasons: list[str] = []
    state_root = Path(args.state_root)
    if include_marker and (state_root / "wud-update.lock").exists():
        reasons.append("WUD update marker exists")
    try:
        with operation_lock(state_root):
            pass
    except RuntimeError:
        reasons.append("reconciler lock is held")
    if inbox_has_work(Path(args.inbox)):
        reasons.append("Storyteller inbox contains pending or importing work")
    active = storyteller_active_jobs(Path(args.database))
    if active:
        reasons.append(f"Storyteller has {active} queued or processing job(s)")
    return reasons


def wud_acquire(args: argparse.Namespace) -> int:
    state_root = Path(args.state_root)
    marker = state_root / "wud-update.lock"
    if marker.exists():
        emit("BUSY WUD update marker already exists")
        return 75
    try:
        with operation_lock(state_root):
            reasons: list[str] = []
            if inbox_has_work(Path(args.inbox)):
                reasons.append("Storyteller inbox contains pending or importing work")
            active = storyteller_active_jobs(Path(args.database))
            if active:
                reasons.append(f"Storyteller has {active} queued or processing job(s)")
            if reasons:
                emit("BUSY " + "; ".join(reasons))
                return 75
            atomic_json_write(marker, {"created_at": now(), "pid": os.getpid()})
    except RuntimeError:
        emit("BUSY reconciler lock is held")
        return 75
    emit("WUD-GUARD-ACQUIRED")
    return 0


def wud_release(args: argparse.Namespace) -> int:
    marker = Path(args.state_root) / "wud-update.lock"
    marker.unlink(missing_ok=True)
    emit("WUD-GUARD-RELEASED")
    return 0


def report(args: argparse.Namespace, full: bool) -> int:
    manifest = load_manifest(Path(args.state_root) / "manifest.json")
    states = Counter(
        item.get("stage_state", "unknown") for item in manifest["items"].values()
    )
    payload: dict[str, Any] = {
        "version": manifest["version"],
        "updated_at": manifest.get("updated_at"),
        "items": len(manifest["items"]),
        "states": dict(sorted(states.items())),
        "active_storyteller_jobs": storyteller_active_jobs(Path(args.database)),
        "inbox_has_work": inbox_has_work(Path(args.inbox)),
    }
    if full:
        payload["manifest_items"] = manifest["items"]
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def database_backup(args: argparse.Namespace) -> int:
    database = Path(args.database)
    if not database.is_file():
        raise RuntimeError(f"Storyteller database is missing: {database}")
    backup_root = Path(args.state_root) / "backups"
    latest = backup_root / "latest"
    previous = backup_root / "previous"
    latest.mkdir(parents=True, exist_ok=True)
    previous.mkdir(parents=True, exist_ok=True)
    temporary = backup_root / f".backup-{uuid.uuid4().hex}.sqlite"
    source = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=30)
    destination = sqlite3.connect(temporary)
    try:
        source.backup(destination)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Storyteller backup integrity is {integrity}")
        tables = {
            row[0]
            for row in destination.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        counts = {
            table: destination.execute(
                f'SELECT count(*) FROM "{table}"'
            ).fetchone()[0]
            for table in ("user", "book", "ebook", "audiobook", "readaloud")
            if table in tables
        }
        destination.commit()
    finally:
        destination.close()
        source.close()
    os.chmod(temporary, 0o600)
    metadata = {
        "created_at": now(),
        "integrity": "ok",
        "counts": counts,
        "sha256": sha256_file(temporary),
        "size": temporary.stat().st_size,
    }
    for name in ("storyteller.db", "metadata.json"):
        current = latest / name
        if current.exists():
            os.replace(current, previous / name)
    os.replace(temporary, latest / "storyteller.db")
    atomic_json_write(latest / "metadata.json", metadata)
    emit(
        "DATABASE-BACKUP "
        + " ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    )
    return 0


def serve(args: argparse.Namespace) -> int:
    state_root = Path(args.state_root)
    heartbeat = state_root / "heartbeat.json"
    while True:
        status = "ok"
        error: str | None = None
        try:
            reconcile(args, dry_run=False)
        except Exception as caught:
            status = "error"
            error = str(caught)
            emit(f"SERVE-ERROR detail={json.dumps(error)}")
        atomic_json_write(
            heartbeat,
            {"updated_at": now(), "epoch": int(time.time()), "status": status, "error": error},
        )
        time.sleep(args.interval_seconds)


def health(args: argparse.Namespace) -> int:
    heartbeat = Path(args.state_root) / "heartbeat.json"
    if not heartbeat.is_file():
        return 1
    with heartbeat.open(encoding="utf-8") as handle:
        state = json.load(handle)
    age = int(time.time()) - int(state.get("epoch", 0))
    if age > args.max_heartbeat_age:
        return 1
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ebook-root", default=str(DEFAULT_EBOOK_ROOT))
    parser.add_argument("--audiobook-root", default=str(DEFAULT_AUDIOBOOK_ROOT))
    parser.add_argument("--inbox", default=str(DEFAULT_INBOX))
    parser.add_argument("--library", default=str(DEFAULT_LIBRARY))
    parser.add_argument("--state-root", default=str(DEFAULT_STATE))
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--max-items", type=int, default=1)
    parser.add_argument("--min-free-gib", type=float, default=50)
    parser.add_argument("--copy-headroom-gib", type=float, default=5)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("reconcile", "dry-run", "status", "report", "busy"):
        add_common(commands.add_parser(name))
    serve_parser = commands.add_parser("serve")
    add_common(serve_parser)
    serve_parser.add_argument("--interval-seconds", type=int, default=900)
    for name in ("wud-acquire", "wud-release", "database-backup"):
        add_common(commands.add_parser(name))
    health_parser = commands.add_parser("health")
    add_common(health_parser)
    health_parser.add_argument("--max-heartbeat-age", type=int, default=1900)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.max_items < 1:
        raise RuntimeError("--max-items must be positive")
    if args.command == "reconcile":
        reconcile(args, dry_run=False)
        return 0
    if args.command == "dry-run":
        reconcile(args, dry_run=True)
        return 0
    if args.command == "status":
        return report(args, full=False)
    if args.command == "report":
        return report(args, full=True)
    if args.command == "busy":
        reasons = busy_reasons(args)
        if reasons:
            emit("BUSY " + "; ".join(reasons))
            return 75
        emit("IDLE")
        return 0
    if args.command == "wud-acquire":
        return wud_acquire(args)
    if args.command == "wud-release":
        return wud_release(args)
    if args.command == "database-backup":
        return database_backup(args)
    if args.command == "serve":
        return serve(args)
    if args.command == "health":
        return health(args)
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        emit(f"FATAL detail={json.dumps(str(error))}")
        raise SystemExit(1)
