#!/usr/bin/env python3
"""Remove terminal import-failed rows from Lidarr without deleting downloads."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

BASE = "http://192.168.0.102:8686/api/v1"


def request(path: str, api_key: str, *, method: str = "GET") -> object:
    call = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        headers={"X-Api-Key": api_key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(call, timeout=30) as response:
        body = response.read()
    return json.loads(body) if body else {}


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def before_cutoff(record: dict[str, object], cutoff: datetime) -> bool:
    added = record.get("added")
    if added is None:
        return True
    try:
        return parse_date(str(added)) <= cutoff
    except ValueError:
        return False


def stale_records(payload: object, cutoff: datetime) -> list[dict[str, object]]:
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("status") == "completed"
        and record.get("trackedDownloadState") == "importFailed"
        and int(record.get("sizeleft", -1)) == 0
        and before_cutoff(record, cutoff)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--minimum-age-days", type=int, default=7)
    args = parser.parse_args()
    api_key = os.environ.get("LIDARR_API_KEY", "")
    if len(api_key) < 16:
        raise RuntimeError("LIDARR_API_KEY is required")

    payload = request("/queue?page=1&pageSize=500&includeUnknownArtistItems=true", api_key)
    cutoff = datetime.now(UTC) - timedelta(days=args.minimum_age_days)
    stale = stale_records(payload, cutoff)
    print(f"Found {len(stale)} terminal import-failed Lidarr queue row(s).")
    if not args.apply:
        print("Dry run only; pass --apply to remove queue metadata.")
        return 0

    query = urllib.parse.urlencode(
        {
            "removeFromClient": "false",
            "blocklist": "false",
            "skipRedownload": "false",
            "changeCategory": "false",
        }
    )
    for record in stale:
        request(f"/queue/{int(record['id'])}?{query}", api_key, method="DELETE")
    remaining = request(
        "/queue?page=1&pageSize=500&includeUnknownArtistItems=true", api_key
    )
    residual = stale_records(remaining, cutoff)
    if residual:
        raise RuntimeError(
            f"{len(residual)} terminal import-failed queue row(s) remain"
        )
    print(
        f"Removed {len(stale)} stale queue row(s); download-client data "
        "and media were retained."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
