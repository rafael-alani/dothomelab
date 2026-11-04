import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit_compare', Path(__file__).with_name('audit-compare.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SourceAuditTests(unittest.TestCase):
    def test_terminal_page_does_not_hide_broken_cursor_chain(self):
        pages = [{'input_cursor_sha256': None, 'next_cursor_sha256': 'a', 'more_available': True},
                 {'input_cursor_sha256': 'a', 'next_cursor_sha256': None, 'more_available': False}]
        self.assertEqual(audit.pagination_proof(pages), [])
        pages[1]['input_cursor_sha256'] = 'wrong'
        self.assertEqual(audit.pagination_proof(pages), ['cursor_chain:1'])
        self.assertEqual(audit.pagination_proof([]), ['no_pages'])

    def test_completion_receipt_does_not_hide_missing_carousel_members(self):
        observation = {'source': 'yaay', 'status': 'complete', 'gaps': [], 'collections': [], 'memberships': [],
                       'items': [{'id': 'saved', 'source_key': 'instagram:post', 'metadata': {'carousel_members': [
                           {'id': 'one', 'ordinal': 0, 'kind': 'image'}, {'id': 'two', 'ordinal': 1, 'kind': 'video'}]}}]}
        ledger = {'source_items': [], 'membership_entries': [], 'collections': [],
                  'assets': [{'id': 'asset', 'path': 'objects/asset.jpg'}],
                  'completed_posts': [{'source_key': 'instagram:post', 'members': [{'id': 'asset', 'ordinal': 0}]}]}
        report = audit.compare(ledger, observation)
        self.assertEqual(report['receipt_discrepancies'][0]['errors'], ['member_count'])
        self.assertEqual(report['new_items'], ['saved'])
