#!/usr/bin/env python3
"""Tests for the fail-closed Aurral request selector."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("request-scoped-soularr.py")
SPEC = importlib.util.spec_from_file_location("request_scoped_soularr", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CLEAR_PATH = Path(__file__).with_name("clear-stale-lidarr-queue.py")
CLEAR_SPEC = importlib.util.spec_from_file_location("clear_stale_queue", CLEAR_PATH)
assert CLEAR_SPEC and CLEAR_SPEC.loader
CLEAR_MODULE = importlib.util.module_from_spec(CLEAR_SPEC)
CLEAR_SPEC.loader.exec_module(CLEAR_MODULE)


class RequestScopedSoularrTests(unittest.TestCase):
    def test_selects_only_valid_ids_inside_age_window(self) -> None:
        now = 2_000_000
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "aurral.db"
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "CREATE TABLE aurral_history "
                    "(kind TEXT, metadata TEXT, created_at INTEGER)"
                )
                connection.executemany(
                    "INSERT INTO aurral_history VALUES (?, ?, ?)",
                    [
                        (
                            "album_requested",
                            json.dumps({"albumId": 1318}),
                            now - 20_000,
                        ),
                        (
                            "album_requested",
                            json.dumps({"albumId": 1311}),
                            now - 30_000,
                        ),
                        (
                            "album_requested",
                            json.dumps({"albumId": 9}),
                            now - 2_000,
                        ),
                        (
                            "album_requested",
                            json.dumps({"albumId": 10}),
                            now - 200_000,
                        ),
                        ("album_requested", "invalid", now - 20_000),
                        (
                            "flow_generated",
                            json.dumps({"albumId": 11}),
                            now - 20_000,
                        ),
                    ],
                )
            result = MODULE.requested_album_ids(
                database,
                now_ms=now,
                delay_seconds=10,
                max_age_seconds=100,
            )
        self.assertEqual(result, {1311, 1318})

    def test_filters_wanted_records_by_release_album_id(self) -> None:
        payload = {
            "page": 3,
            "pageSize": 50,
            "totalRecords": 500,
            "records": [
                {"id": 1, "releases": [{"albumId": 1318}]},
                {"id": 2, "releases": [{"albumId": 99}]},
            ],
        }
        result = MODULE.filter_wanted(payload, {1318})
        self.assertEqual([record["id"] for record in result["records"]], [1])
        self.assertEqual(result["totalRecords"], 1)

    def test_terminal_queue_row_without_added_date_is_selectable(self) -> None:
        payload = {
            "records": [
                {
                    "id": 23,
                    "status": "completed",
                    "trackedDownloadState": "importFailed",
                    "sizeleft": 0,
                },
                {
                    "id": 24,
                    "status": "downloading",
                    "trackedDownloadState": "downloading",
                    "sizeleft": 10,
                },
            ]
        }
        result = CLEAR_MODULE.stale_records(
            payload, datetime(2026, 7, 26, tzinfo=UTC)
        )
        self.assertEqual([record["id"] for record in result], [23])


if __name__ == "__main__":
    unittest.main()
