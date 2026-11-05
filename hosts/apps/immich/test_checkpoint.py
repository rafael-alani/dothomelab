#!/usr/bin/env python3
"""Reject incomplete/ambiguous SQL count receipts before accepting a restore."""
import unittest
from checkpoint import counts, database_mount


class CountReceiptTests(unittest.TestCase):
    def test_restore_uses_checkpoint_layout_across_postgres_major_change(self):
        for destination in ('/var/lib/postgresql/data', '/var/lib/postgresql'):
            self.assertEqual(database_mount({'mounts': [{'destination': destination}]}), destination)
        with self.assertRaises(ValueError):
            database_mount({'mounts': [{'destination': '/unexpected'}]})
        with self.assertRaises(ValueError):
            database_mount({'mounts': [{'destination': '/var/lib/postgresql'},
                                       {'destination': '/var/lib/postgresql/data'}]})

    def test_complete(self):
        self.assertEqual(counts(['["public.asset", 27]', '["public.album", 0]', '"END"']),
                         {'public.asset': 27, 'public.album': 0})

    def test_incomplete_or_invalid(self):
        for rows in (['["public.asset", 27]'],
                     ['["public.asset", -1]', '"END"'],
                     ['["public.asset", true]', '"END"'],
                     ['["public.asset", 1]', '["public.asset", 2]', '"END"']):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                counts(rows)


if __name__ == '__main__':
    unittest.main()
