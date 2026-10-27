import unittest
import run

class EventTests(unittest.TestCase):
    def test_index_event_for_vault_triggers_export(self):
        self.assertTrue(run.relevant([{'data': {'folder': 'vault', 'filenames': ['Blog/article.md']}}], 'vault'))
        self.assertTrue(run.relevant([{'data': {'folder': 'vault', 'filenames': ['Notes/source.md']}}], 'vault'))
    def test_unrelated_folder_and_settings_do_not_trigger(self):
        self.assertFalse(run.relevant([{'data': {'folder': 'other', 'filenames': ['Blog/article.md']}}], 'vault'))
        self.assertFalse(run.relevant([{'data': {'folder': 'vault', 'filenames': ['.obsidian/workspace.json']}}], 'vault'))

if __name__ == '__main__':
    unittest.main()
