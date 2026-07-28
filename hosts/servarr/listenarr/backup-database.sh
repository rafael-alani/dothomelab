#!/usr/bin/env bash
set -Eeuo pipefail

readonly database="/docker/listenarr/database/listenarr.db"
readonly backup_root="/docker/listenarr/backups"
readonly lock="/run/lock/dothomelab-listenarr-database.lock"

[[ -s "$database" ]] || {
  echo "Listenarr database is missing: $database" >&2
  exit 1
}
[[ "$(docker inspect --format '{{.State.Status}}' listenarr)" == "running" ]] || {
  echo "Listenarr container is not running" >&2
  exit 1
}

exec 9>"$lock"
flock -n 9 || {
  echo "Another Listenarr database backup is already running" >&2
  exit 1
}

python3 - "$database" "$backup_root" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

database = Path(sys.argv[1])
backup_root = Path(sys.argv[2])
latest = backup_root / "latest"
previous = backup_root / "previous"
latest.mkdir(parents=True, exist_ok=True)
previous.mkdir(parents=True, exist_ok=True)

descriptor, temporary_name = tempfile.mkstemp(
    prefix=".listenarr-", suffix=".db", dir=backup_root
)
os.close(descriptor)
temporary = Path(temporary_name)
try:
    source = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=30)
    destination = sqlite3.connect(temporary)
    try:
        source.backup(destination)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Listenarr backup integrity is {integrity}")
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
            for table in (
                "Audiobooks",
                "Downloads",
                "DownloadClientConfigurations",
                "Indexers",
                "QualityProfiles",
                "RootFolders",
                "Users",
            )
            if table in tables
        }
        destination.commit()
    finally:
        destination.close()
        source.close()

    os.chmod(temporary, 0o600)
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    metadata = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "integrity": "ok",
        "counts": counts,
        "sha256": digest,
        "size": temporary.stat().st_size,
    }

    for name in ("listenarr.db", "metadata.json"):
        current = latest / name
        if current.exists():
            os.replace(current, previous / name)
    os.replace(temporary, latest / "listenarr.db")

    metadata_path = latest / "metadata.json"
    meta_descriptor, meta_temporary_name = tempfile.mkstemp(
        prefix=".metadata-", dir=latest, text=True
    )
    try:
        os.fchmod(meta_descriptor, 0o600)
        with os.fdopen(meta_descriptor, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(meta_temporary_name, metadata_path)
    finally:
        try:
            os.unlink(meta_temporary_name)
        except FileNotFoundError:
            pass
    os.chmod(metadata_path, 0o600)
    print(
        "Listenarr SQLite online backup passed integrity verification; "
        f"tables={len(counts)}"
    )
finally:
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
PY
