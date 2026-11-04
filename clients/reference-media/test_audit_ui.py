import unittest
import json
from pathlib import Path
import subprocess
import tempfile

from audit_yaay_ui import image_key


class UiIdentityTests(unittest.TestCase):
    def test_same_count_and_identities_do_not_hide_picker_order_difference(self):
        ledger = {'collections': [{'source': 'yaay', 'id': 'b:b', 'parent': None, 'ordinal': 1},
                                  {'source': 'yaay', 'id': 'g:g', 'parent': 'b:b', 'ordinal': 1}],
                  'source_items': [{'source': 'yaay', 'id': key, 'source_key': 'instagram:' + key} for key in ('A', 'B')],
                  'membership_entries': [{'source': 'yaay', 'item_id': key, 'collection_id': 'g:g',
                                          'ordinal': 1, 'active': 1} for key in ('A', 'B')]}
        ui = {'root_ids': ['b'], 'boards': [{'id': 'b:b', 'section_order': ['g:g'], 'gaps': [],
              'sections': [{'id': 'g:g', 'title': 'Group', 'cards': [{'ids': ['B']}, {'ids': ['A']}]}]}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'server.json').write_text(json.dumps(ledger))
            (root / 'ui.json').write_text(json.dumps(ui))
            output = subprocess.check_output(['node', str(Path(__file__).with_name('audit-ui-order.cjs')),
                                              str(root / 'server.json'), str(root / 'ui.json')], text=True)
        section = json.loads(output)['sections'][0]
        self.assertTrue(section['identities_equal'])
        self.assertFalse(section['order_equal'])

    def test_resize_wrapper_and_cache_query_do_not_change_thumbnail_identity(self):
        original = 'https://vdn.example/saved/thumb.jpg?cache=first'
        rendered = 'https://images.example/cdn-cgi/image/width=230/https://vdn.example/saved/thumb.jpg?cache=second'
        self.assertEqual(image_key(original), image_key(rendered))
        self.assertNotEqual(image_key(original), image_key('https://vdn.example/saved/different.jpg'))
        self.assertIsNone(image_key(None))
