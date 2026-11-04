import unittest
from reconcile import reconcile


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {'items': [{'source': 'instagram', 'id': '1', 'source_key': 'instagram:OLD'}],
                        'collections': [{'source': 'instagram', 'id': 'grind', 'title': 'Grind', 'ordinal': 3, 'parent': None}],
                        'memberships': [{'source': 'instagram', 'collection_id': 'grind', 'item_id': '1', 'active': 1}],
                        'assets': [], 'acquisitions': []}
        self.observation = {'source': 'instagram', 'collection': {'id': 'grind'},
                            'pagination_complete': True, 'pages': [1], 'observed_at': 123,
                            'source_keys': ['instagram:NEW'], 'grid_keys': ['instagram:NEW'],
                            'items': [{'id': '2', 'source_key': 'instagram:NEW', 'metadata': {'carousel_members': [{'kind': 'video'}]}}]}

    def test_scoped_reconciliation_never_certifies_whole_source_or_retires_absent_posts(self):
        doc, report, absent = reconcile(self.catalog, self.observation)
        self.assertEqual(doc['status'], 'partial')
        self.assertEqual(absent, ['instagram:OLD'])
        self.assertEqual(report[0]['acquisition'], 'pending')
        self.assertEqual(report[0]['archived_files'], 0)
        self.assertEqual(doc['completion']['collection_audits']['grind']['ui_posts'], 1)
        self.assertEqual(self.catalog['memberships'][0]['active'], 1)

    def test_order_and_page_coverage_must_match(self):
        for name, value in [('grid_keys', ['instagram:DIFFERENT']), ('pages', [2]), ('pagination_complete', False)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                reconcile(self.catalog, dict(self.observation, **{name: value}))
