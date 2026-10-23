#!/usr/bin/env python3
"""Verify stopped-database checks without live services or credentials."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('migration', Path(__file__).with_name('migrate-from-staging.py'))
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class MigrationChecks(unittest.TestCase):
    def test_count_all_tables_and_handle_quoted_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'grafana.db'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE dashboard (id INTEGER)')
                db.executemany('INSERT INTO dashboard VALUES (?)', [(1,), (2,)])
                db.execute('CREATE TABLE "odd""table" (id INTEGER)')
            self.assertEqual(migration.checked_sqlite(path), {'dashboard': 2, 'odd"table': 0})

    def test_missing_and_corrupt_database_are_never_created_or_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'grafana.db'
            with self.assertRaises(sqlite3.Error):
                migration.checked_sqlite(path)
            self.assertFalse(path.exists())
            path.write_bytes(b'not a sqlite database')
            with self.assertRaises(sqlite3.Error):
                migration.checked_sqlite(path)


if __name__ == '__main__':
    unittest.main()
