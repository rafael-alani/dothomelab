import copy
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from archive import Archive


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'media').mkdir()
        (self.root / 'state').mkdir()
        self.archive = Archive(self.root / 'media', self.root / 'state')
        self.body = b'immutable fixture media'
        self.digest = hashlib.sha256(self.body).hexdigest()
        self.header = {'sha256': self.digest, 'extension': 'mp4', 'bytes': len(self.body)}
        self.document = {
            'source': 'yaay', 'scan_id': 'one', 'status': 'complete',
            'completion': {'authenticated': True, 'pagination_complete': True,
                           'roots_complete': True, 'visited_collections': 4},
            'collections': [
                {'id': 'root', 'parent': None, 'title': 'Trip', 'ordinal': 0},
                {'id': 'one', 'parent': 'root', 'title': 'Repeat', 'ordinal': 0},
                {'id': 'two', 'parent': 'one', 'title': 'Repeat', 'ordinal': 0},
                {'id': 'empty', 'parent': 'root', 'title': 'Empty', 'ordinal': 1}],
            'items': [{'id': 'saved', 'source_key': 'instagram:ABC', 'url': 'https://www.instagram.com/p/ABC/',
                       'metadata': {'title': 'Reference', 'places': [{'label': 'Place', 'provenance': 'yaay'}]}}],
            'memberships': [{'collection_id': c, 'item_id': 'saved', 'ordinal': 0} for c in ('one', 'two')]}

    def tearDown(self):
        self.archive.db.close()
        self.tmp.cleanup()

    def test_idempotence_cross_source_membership_and_immutable_content(self):
        first = self.archive.put(self.header, io.BytesIO(self.body))
        self.archive.put(self.header, io.BytesIO(self.body))
        self.archive.inventory(self.document)
        self.archive.inventory(self.document)
        self.archive.link({'source_key': 'instagram:ABC', 'ordinal': 0, 'asset_id': self.digest})
        second = copy.deepcopy(self.document)
        second.update(source='instagram', scan_id='instagram-one')
        self.archive.inventory(second)
        self.assertEqual(self.archive.status()['counts']['assets'], 1)
        self.assertEqual(len(self.archive.catalog()['assets'][0]['memberships']), 4)
        self.assertEqual((self.root / 'media' / first['path']).read_bytes(), self.body)
        self.assertEqual(len(list((self.root / 'media/objects').iterdir())), 1)

    def test_rename_reparent_empty_lists_and_unsaving_keep_media(self):
        self.archive.put(self.header, io.BytesIO(self.body))
        self.archive.inventory(self.document)
        self.archive.link({'source_key': 'instagram:ABC', 'ordinal': 0, 'asset_id': self.digest})
        changed = copy.deepcopy(self.document)
        changed['scan_id'] = 'renamed'
        changed['collections'][1]['title'] = 'New name'
        changed['collections'][2]['parent'] = 'root'
        changed['memberships'] = []
        self.archive.inventory(changed)
        catalog = self.archive.catalog()
        self.assertEqual(len(catalog['assets']), 1)
        self.assertEqual(len(catalog['collections']), 4)
        self.assertTrue(all(not m['active'] for m in catalog['assets'][0]['memberships']))
        self.assertEqual(self.archive.db.execute('SELECT count(*) FROM scans').fetchone()[0], 2)
        self.assertEqual((self.root / 'media/objects' / (self.digest + '.mp4')).read_bytes(), self.body)

    def test_partial_scan_never_clears_prior_memberships(self):
        self.archive.inventory(self.document)
        partial = dict(source='yaay', scan_id='interrupted', status='needs_sign_in',
                       collections=[], items=[], memberships=[])
        self.archive.inventory(partial)
        self.assertEqual(self.archive.db.execute('SELECT sum(active) FROM membership_entries').fetchone()[0], 2)
        partial.update(scan_id='pretend-success', status='complete')
        with self.assertRaisesRegex(ValueError, 'completion'):
            self.archive.inventory(partial)

    def test_distinct_repeated_entries_and_completion_receipt(self):
        self.document['memberships'] = [dict(collection_id='one', item_id='saved', ordinal=i, source_membership_id=str(i)) for i in range(2)]
        self.archive.inventory(self.document)
        self.assertEqual(self.archive.status()['counts']['memberships'], 2)
        self.archive.put(self.header, io.BytesIO(self.body))
        receipt = {'source_key': 'instagram:ABC', 'assets': [{'id': self.digest, 'ordinal': 0}]}
        with self.assertRaisesRegex(ValueError, 'missing_carousel'):
            self.archive.complete_post(receipt)
        self.archive.link({'source_key': 'instagram:ABC', 'ordinal': 0, 'asset_id': self.digest})
        self.archive.complete_post(receipt)
        self.archive.complete_post(receipt)
        self.assertEqual(self.archive.pending(), [])
        self.assertEqual(self.archive.status()['counts']['completed_posts'], 1)
        self.assertEqual(self.archive.catalog()['acquisitions'], [{'source_key': 'instagram:ABC', 'status': 'archived', 'members': receipt['assets']}])

    def test_interrupted_or_corrupt_upload_creates_no_asset(self):
        for body in (self.body[:-1], b'x' * len(self.body)):
            with self.assertRaises(ValueError):
                self.archive.put(self.header, io.BytesIO(body))
        self.assertEqual(list((self.root / 'media/objects').iterdir()), [])
        self.assertEqual(self.archive.status()['counts']['assets'], 0)

    def test_cycles_and_conflicting_scan_retry_fail_atomically(self):
        broken = copy.deepcopy(self.document)
        broken['collections'][0]['parent'] = 'two'
        with self.assertRaisesRegex(ValueError, 'hierarchy'):
            self.archive.inventory(broken)
        self.assertEqual(self.archive.status()['counts']['collections'], 0)
        self.archive.inventory(self.document)
        broken = copy.deepcopy(self.document)
        broken['collections'][0]['title'] = 'different retry'
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.archive.inventory(broken)


if __name__ == '__main__':
    unittest.main()
