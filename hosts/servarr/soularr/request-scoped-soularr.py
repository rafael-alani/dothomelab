#!/usr/bin/env python3
"""Run one Soularr cycle for recent album requests recorded by Aurral v2."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

DEFAULT_DB = Path("/docker/aurral/data/aurral.db")
SOULARR = Path("/app/soularr.py")
DEFAULT_ATTEMPTS = Path("/data/request-scoped-attempts.json")


def requested_album_ids(
    database: Path,
    *,
    now_ms: int,
    delay_seconds: int,
    max_age_seconds: int,
) -> set[int]:
    """Return eligible Lidarr album IDs, failing closed on invalid history."""
    uri = f"file:{database}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'aurral_history'"
        ).fetchone()
        if not exists:
            raise RuntimeError("Aurral v2 history table is missing")
        rows = connection.execute(
            "SELECT metadata, created_at FROM aurral_history "
            "WHERE kind = 'album_requested'"
        ).fetchall()

    minimum_age = delay_seconds * 1000
    maximum_age = max_age_seconds * 1000
    selected: set[int] = set()
    for raw_metadata, created_at in rows:
        age = now_ms - int(created_at)
        if age < minimum_age or age > maximum_age:
            continue
        try:
            metadata = json.loads(raw_metadata or "{}")
            album_id = int(metadata["albumId"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if album_id > 0:
            selected.add(album_id)
    return selected


def filter_wanted(payload: object, album_ids: set[int]) -> dict[str, Any]:
    """Filter a Lidarr wanted response to releases for selected albums."""
    if not isinstance(payload, dict):
        return {"page": 1, "pageSize": 1, "totalRecords": 0, "records": []}
    records = payload.get("records")
    if not isinstance(records, list):
        records = []
    selected = []
    for record in records:
        releases = record.get("releases", []) if isinstance(record, dict) else []
        if (
            isinstance(record, dict)
            and record.get("id") in album_ids
        ) or any(
            isinstance(release, dict) and release.get("albumId") in album_ids
            for release in releases
        ):
            selected.append(record)
    return {
        **payload,
        "page": 1,
        "pageSize": max(1, len(selected)),
        "totalRecords": len(selected),
        "records": selected,
    }


def due_album_ids(
    album_ids: set[int],
    attempts_path: Path,
    *,
    now_ms: int,
    retry_seconds: int,
) -> set[int]:
    if not attempts_path.exists():
        return album_ids
    try:
        attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Soularr request-attempt ledger is invalid") from error
    if not isinstance(attempts, dict):
        raise RuntimeError("Soularr request-attempt ledger is not an object")
    retry_ms = retry_seconds * 1000
    return {
        album_id
        for album_id in album_ids
        if now_ms - int(attempts.get(str(album_id), 0)) >= retry_ms
    }


def record_attempts(
    attempts_path: Path,
    album_ids: set[int],
    *,
    now_ms: int,
    max_age_seconds: int,
) -> None:
    attempts: dict[str, int] = {}
    if attempts_path.exists():
        try:
            loaded = json.loads(attempts_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("Soularr request-attempt ledger is invalid") from error
        if not isinstance(loaded, dict):
            raise RuntimeError("Soularr request-attempt ledger is not an object")
        attempts = {
            str(key): int(value)
            for key, value in loaded.items()
            if now_ms - int(value) <= max_age_seconds * 1000
        }
    attempts.update({str(album_id): now_ms for album_id in album_ids})
    attempts_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{attempts_path.name}.", dir=attempts_path.parent, text=True
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(attempts, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, attempts_path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def load_soularr(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("dothomelab_soularr", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Soularr from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scoped_get_wanted(
    original: Callable[..., object], album_ids: set[int]
) -> Callable[..., dict[str, Any]]:
    def get_wanted(*args: object, **kwargs: object) -> dict[str, Any]:
        wanted: list[dict[str, Any]] = []
        page = 1
        while True:
            call_kwargs = {**kwargs, "page": page, "page_size": 1000}
            payload = original(*args, **call_kwargs)
            filtered = filter_wanted(payload, album_ids)
            wanted.extend(filtered["records"])
            if not isinstance(payload, dict):
                break
            total = int(payload.get("totalRecords", 0))
            if page * 1000 >= total:
                break
            page += 1
        return {
            "page": 1,
            "pageSize": max(1, len(wanted)),
            "totalRecords": len(wanted),
            "records": wanted,
        }

    return get_wanted


def main() -> int:
    database = Path(os.environ.get("AURRAL_HISTORY_DB", str(DEFAULT_DB)))
    attempts_path = Path(
        os.environ.get("SOULARR_REQUEST_ATTEMPTS", str(DEFAULT_ATTEMPTS))
    )
    delay = int(os.environ.get("SOULARR_REQUEST_FALLBACK_DELAY_SECONDS", "600"))
    retry = int(os.environ.get("SOULARR_REQUEST_RETRY_SECONDS", str(6 * 60 * 60)))
    max_age = int(
        os.environ.get("SOULARR_REQUEST_MAX_AGE_SECONDS", str(7 * 24 * 60 * 60))
    )
    now_ms = int(time.time() * 1000)
    album_ids = requested_album_ids(
        database,
        now_ms=now_ms,
        delay_seconds=delay,
        max_age_seconds=max_age,
    )
    album_ids = due_album_ids(
        album_ids,
        attempts_path,
        now_ms=now_ms,
        retry_seconds=retry,
    )
    if not album_ids:
        print(
            "No due recent Aurral album requests; Soularr cycle skipped."
        )
        return 0

    module = load_soularr(SOULARR)
    original = module.LidarrAPI.get_wanted
    module.LidarrAPI.get_wanted = scoped_get_wanted(original, album_ids)
    print(
        f"Starting request-scoped Soularr cycle for {len(album_ids)} "
        "recent Aurral album request(s)."
    )
    try:
        return int(module.main() or 0)
    finally:
        record_attempts(
            attempts_path,
            album_ids,
            now_ms=now_ms,
            max_age_seconds=max_age,
        )


if __name__ == "__main__":
    raise SystemExit(main())
