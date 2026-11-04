import copy
import unittest
from inventory import yaay_document, public_url
from collector import YaayCapture
from instagram import normalize


class InventoryTests(unittest.TestCase):
    def test_recursive_empty_repeated_lists_and_duplicate_memberships(self):
        saved = {'s': {'item': {'id': 's', 'externalUrl': 'https://instagram.com/reel/ABC/?igsh=secret', 'createdAt': '2026-11-04 10:00:00'}, 'matches': []}}
        child = {'id': 'inner', 'title': 'Same', 'weight': 1, 'items': [{'id': 'a', 'savedId': 's', 'weight': 0}, {'id': 'b', 'savedId': 's', 'weight': 1}]}
        group = {'id': 'outer', 'title': 'Same', 'weight': 0, 'groups': [child, {'id': 'empty', 'title': '', 'weight': 2}], 'items': []}
        boards = {'root': {'item': {'id': 'root', 'title': 'Trip', 'weight': 0}, 'groups': [group], 'itemCount': 2}}
        document, _ = yaay_document(boards, saved)
        self.assertEqual(document['gaps'], [])
        self.assertEqual(next(c for c in document['collections'] if c['id'] == 'g:inner')['parent'], 'g:outer')
        self.assertEqual(len([m for m in document['memberships'] if m['collection_id'] == 'g:inner']), 2)
        self.assertEqual(document['items'][0]['url'], 'https://www.instagram.com/p/ABC/')
        self.assertEqual(document['items'][0]['metadata']['source_saved'], '2026-11-04 10:00:00')
        self.assertIsNone(document['items'][0]['metadata']['source_created'])
        changed = copy.deepcopy(boards)
        changed['root']['groups'] = [dict(group, groups=[]), dict(child, title='Renamed')]
        updated, _ = yaay_document(changed, saved)
        self.assertEqual(next(c for c in updated['collections'] if c['id'] == 'g:inner')['parent'], 'b:root')

    def test_incremental_terminal_page_cannot_complete_full_scan(self):
        class Request:
            post_data_json = {'variables': {'filter': {'include': 'all'}, 'checkpoint': {'updatedAt': 'earlier'}}}
        class Response:
            url = 'https://yaaytravel.com/graphql'
            status = 200
            request = Request()
            def json(self):
                return {'data': {'saved': {'updates': {'edges': [], 'pageInfo': {'hasNextPage': False}}}}}
        capture = YaayCapture()
        capture.response(Response())
        self.assertFalse(capture.complete['saved'])
        self.assertEqual(capture.pages['saved'], 0)

    def test_place_link_keeps_routing_arguments_without_tracking(self):
        self.assertEqual(public_url('https://www.google.com/maps/search/?api=1&query=Gallery&query_place_id=place123&token=secret'),
                         'https://www.google.com/maps/search/?api=1&query=Gallery&query_place_id=place123')

    def test_instagram_keeps_carousel_and_place_provenance_without_cdn_tokens(self):
        result = normalize({'pk': 123, 'code': 'ABC', 'caption': {'text': 'Title\nCaption'}, 'user': {'username': 'creator'},
                            'location': {'pk': 4, 'name': 'Place', 'lat': 1, 'lng': 2},
                            'carousel_media': [{'pk': 5, 'media_type': 1}, {'pk': 6, 'media_type': 2, 'video_versions': [{'url': 'signed-secret'}]}]})
        self.assertEqual(len(result['metadata']['carousel_members']), 2)
        self.assertEqual(result['metadata']['places'][0]['provenance'], 'instagram_location_tag')
        self.assertNotIn('signed-secret', str(result))

class ResumeTests(unittest.TestCase):
    def test_collection_disagreement_retries_then_rebuilds_unfiled(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from instagram import advance, shortcode_id
        root = [{'id': cid, 'title': cid, 'parent': None, 'ordinal': n,
                 'url': f'https://www.instagram.com/fixture/saved/{slug}/'}
                for n, (cid, slug) in enumerate([('all', 'all-posts'), ('123', 'grind/123')])]
        calls = []
        def page(_self, endpoint, **kwargs):
            calls.append(endpoint)
            codes = ['A'] if len(calls) == 1 else ['B'] if len(calls) == 2 else ['A', 'C']
            return {'status': 'ok', 'more_available': False,
                    'items': [{'media': {'pk': int(shortcode_id(code)), 'code': code}} for code in codes]}
        def rows(codes):
            return [{'code': code, 'url': f'/creator/reel/{code}/', 'caption': code, 'kind': 'video'} for code in codes]
        cookies = [{'name': 'sessionid', 'value': 'fixture-only', 'domain': '.instagram.com'}]
        with tempfile.TemporaryDirectory() as folder, patch('instagram.roots', return_value=root), \
                patch('gallery_dl.extractor.instagram.InstagramAPI._call', page), \
                patch('instagram.collection_grid', side_effect=[rows(['C']), rows(['A', 'C'])]):
            checkpoint = Path(folder) / 'scan.json'
            first = advance(None, cookies, root[0]['url'], checkpoint)
            self.assertEqual(first['status'], 'partial')
            self.assertFalse(first['completion']['pagination_complete'])
            self.assertEqual(first['gaps'], ['instagram_api_ui_disagreement_retry'])
            self.assertEqual({m['item_id'] for m in first['memberships'] if m['collection_id'] == '123'},
                             {shortcode_id('B'), shortcode_id('C')})
            second = advance(None, cookies, root[0]['url'], checkpoint)
            self.assertEqual(second['status'], 'complete')
            self.assertEqual(second['gaps'], [])
            self.assertFalse(any(m['collection_id'] == 'unfiled' for m in second['memberships']))
            self.assertEqual([m['item_id'] for m in second['memberships'] if m['collection_id'] == '123'],
                             [shortcode_id('A'), shortcode_id('C')])
            self.assertEqual(len(calls), 3, 'only the disputed collection is rescanned')

    def test_page_budget_resumes_without_false_completion_or_duplicate_membership(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from instagram import advance
        root = [{'id': 'all', 'title': 'All Posts', 'parent': None, 'ordinal': 0, 'url': 'https://www.instagram.com/fixture/saved/all-posts/'}]
        def page(_self, endpoint, **kwargs):
            cursor = kwargs['params'].get('max_id')
            self.assertIn(cursor, (None, 'second'))
            return {'status': 'ok', 'more_available': cursor is None, 'next_max_id': 'second' if cursor is None else None,
                    'items': [{'media': {'pk': 1 if cursor is None else 2, 'code': 'A' if cursor is None else 'B'}}]}
        cookies = [{'name': 'sessionid', 'value': 'fixture-only', 'domain': '.instagram.com'}]
        with tempfile.TemporaryDirectory() as folder, patch('instagram.roots', return_value=root), patch('gallery_dl.extractor.instagram.InstagramAPI._call', page):
            checkpoint = Path(folder) / 'scan.json'
            first = advance(None, cookies, root[0]['url'], checkpoint, page_budget=1)
            self.assertEqual(first['status'], 'partial')
            self.assertEqual(len(first['items']), 1)
            second = advance(None, cookies, root[0]['url'], checkpoint, page_budget=1)
            self.assertEqual(second['status'], 'complete')
            self.assertEqual(len(second['items']), 2)
            self.assertEqual(len(second['memberships']), 4)
            self.assertEqual(second['completion']['pages'], 2)
            daily = advance(None, cookies, root[0]['url'], Path(folder) / 'daily.json', page_budget=None)
            self.assertEqual(daily['status'], 'complete')
            self.assertEqual(len(daily['items']), 2)
            self.assertEqual(daily['completion']['pages'], 2)

    def test_metadata_refresh_preserves_annotations_and_project(self):
        import tempfile
        from pathlib import Path
        from publish import managed
        with tempfile.TemporaryDirectory() as folder:
            note = Path(folder) / 'source.md'
            managed(note, 'First source title')
            note.write_text(note.read_text() + '\nKeep my idea.\n')
            managed(note, 'Renamed source title')
            self.assertIn('Keep my idea.', note.read_text())
            self.assertIn('Renamed source title', note.read_text())
            self.assertNotIn('First source title', note.read_text())


if __name__ == '__main__':
    unittest.main()

class GridReconciliationTests(unittest.TestCase):
    def test_ui_only_posts_are_pending_and_order_is_not_publication_order(self):
        from instagram import reconcile_grid, shortcode_id
        document = {'items': [{'id': shortcode_id('ABC'), 'source_key': 'instagram:ABC', 'metadata': {'source_created': 123}}],
                    'memberships': [{'collection_id': 'grind', 'item_id': shortcode_id('ABC'), 'ordinal': 0}]}
        rows = [{'code': 'NEW', 'url': '/creator/reel/NEW/', 'caption': 'New post', 'kind': 'video'},
                {'code': 'ABC', 'url': '/creator/p/ABC/', 'caption': 'Old', 'kind': 'image'}]
        audit = reconcile_grid(document, 'grind', rows)
        self.assertEqual(audit['ui_only'], ['instagram:NEW'])
        self.assertEqual(audit['api_only'], [])
        self.assertEqual(document['memberships'][0]['item_id'], shortcode_id('NEW'))
        new = next(i for i in document['items'] if i['source_key'] == 'instagram:NEW')
        self.assertIsNone(new['metadata']['source_created'])
        self.assertEqual(new['metadata']['media_kind'], 'video')
        self.assertNotIn('assets', new)
        self.assertEqual(next(i for i in document['items'] if i['source_key'] == 'instagram:ABC')['metadata']['source_created'], 123)

    def test_grid_mismatch_retains_api_only_identity_and_reports_gap(self):
        from instagram import reconcile_grid, shortcode_id
        document = {'items': [{'id': shortcode_id('OLD'), 'source_key': 'instagram:OLD', 'metadata': {}}],
                    'memberships': [{'collection_id': 'grind', 'item_id': shortcode_id('OLD'), 'ordinal': 0}]}
        audit = reconcile_grid(document, 'grind', [{'code': 'NEW', 'url': '/creator/reel/NEW/', 'caption': '', 'kind': 'video'}])
        self.assertEqual(audit['api_only'], ['instagram:OLD'])
        self.assertEqual(len(document['memberships']), 2)
        with self.assertRaises(ValueError):
            reconcile_grid(document, 'grind', [])

    def test_shortcode_identity_matches_observed_native_id(self):
        from instagram import shortcode_id
        self.assertEqual(shortcode_id('DcA4Tpgy0V6'), '3963415312934323578')
