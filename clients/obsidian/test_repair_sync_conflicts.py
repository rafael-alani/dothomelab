import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('repair', Path(__file__).with_name('repair-sync-conflicts.py'))
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'vault'
        self.root.mkdir()
        self.recovery = self.base / 'recovery'

    def put(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_unique_bytes_are_verified_archived_and_restorable(self):
        name = 'note.sync-conflict-20261105-120000-DEVICE.md'
        path = self.put(name, b'Unique user content\x00')
        plan = repair.save_plan(self.root, self.recovery, repair.cleanup(self.root))
        self.assertEqual(repair.blob(self.recovery, plan['entries'][0]['before']), path.read_bytes())
        repair.apply(self.recovery)
        self.assertFalse(path.exists())
        repair.apply(self.recovery, name)
        self.assertEqual(path.read_bytes(), b'Unique user content\x00')

    def test_concurrent_change_aborts_before_any_delete(self):
        self.put('a', b'one')
        path = self.put('b', b'two')
        repair.save_plan(self.root, self.recovery, [('a', None, 'test'), ('b', None, 'test')])
        path.write_bytes(b'new edit')
        with self.assertRaisesRegex(ValueError, 'changed since planning'):
            repair.apply(self.recovery)
        self.assertTrue((self.root / 'a').exists())
        self.assertEqual(path.read_bytes(), b'new edit')

    def test_tampered_recovery_aborts_delete(self):
        path = self.put('a', b'original')
        plan = repair.save_plan(self.root, self.recovery, [('a', None, 'test')])
        (self.recovery / (plan['entries'][0]['before'] + '.blob')).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'verification failed'):
            repair.apply(self.recovery)
        self.assertTrue(path.exists())

    def test_symlink_cannot_escape_vault(self):
        outside = self.base / 'outside'
        outside.write_bytes(b'private')
        (self.root / 'link.sync-conflict-test').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            repair.cleanup(self.root)
        self.assertEqual(outside.read_bytes(), b'private')

    def test_only_empty_generated_documents_are_recovered(self):
        navigation = b'%% Begin Waypoint %%\n- [[old.sync-conflict-x]]\n%% End Waypoint %%\n'
        body = repair.PREFIX + b'\nUser text\n' + navigation
        self.put('05. Docs/example.md', navigation)
        self.put('05. Docs/example.sync-conflict-20261105-120000-DEVICE.md', body)
        self.put('05. Docs/edited.md', b'New author text')
        self.put('05. Docs/edited.sync-conflict-20261105-120000-DEVICE.md', body)
        repair.save_plan(self.root, self.recovery, repair.cleanup(self.root))
        repair.apply(self.recovery)
        self.assertEqual((self.root / '05. Docs/example.md').read_bytes(), repair.clean_links(body))
        self.assertEqual((self.root / '05. Docs/edited.md').read_bytes(), b'New author text')

    def test_conflicting_recovery_bodies_fail_closed(self):
        self.put('05. Docs/example.md', b'%% Waypoint %%')
        for device in ['ONE', 'TWO']:
            self.put(f'05. Docs/example.sync-conflict-20261105-120000-{device}.md', repair.PREFIX + device.encode())
        with self.assertRaisesRegex(ValueError, 'manual reconciliation'):
            repair.cleanup(self.root)


if __name__ == '__main__':
    unittest.main()
