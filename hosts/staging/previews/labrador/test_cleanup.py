import importlib.util
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).with_name('cleanup.py'))
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.identifier = '123456789a-12345678'
        self.directory = self.root / self.identifier
        self.directory.mkdir()
        self.environ = {'BRANCHLINE_PREVIEW_ID': self.identifier,
                        'BRANCHLINE_PREVIEW_DIR': str(self.directory),
                        'COMPOSE_PROJECT_NAME': 'bl-' + self.identifier}
        self.patch = patch.object(cleanup, 'PREVIEWS', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.recovery = self.root / 'recovery'
        recovery_patch = patch.object(cleanup, 'RECOVERY', self.recovery)
        recovery_patch.start()
        self.addCleanup(recovery_patch.stop)

    def test_verifies_recovery_then_removes_live_data_and_is_repeatable(self):
        for name in ['build-core', 'build-skills', 'mysql', 'seed-state', 'source']:
            (self.directory / name).mkdir()
            (self.directory / name / 'file').write_text(name)
        (self.directory / 'preview.log').write_text('logs')
        calls = []
        def docker(*args):
            calls.append(args)
            return 'image-id' if args[:2] == ('image', 'ls') else ''
        with patch.object(cleanup, 'docker', side_effect=docker), patch.object(cleanup, 'mountpoints', return_value=[]):
            cleanup.cleanup(self.environ)
            cleanup.cleanup(self.environ)
        self.assertFalse(self.directory.exists())
        archive = self.recovery / (self.identifier + '.tar.gz')
        self.assertEqual(json.loads(archive.with_suffix('').with_suffix('.json').read_text())['sha256'], cleanup.digest(archive))
        restored = self.root / 'restored'
        with tarfile.open(archive) as saved:
            saved.extractall(restored, filter='data')
        for name in ['mysql', 'seed-state', 'source']:
            self.assertEqual((restored / name / 'file').read_text(), name)
        self.assertFalse((restored / 'build-core').exists())
        self.assertFalse((restored / 'build-skills').exists())
        self.assertEqual((restored / 'preview.log').read_text(), 'logs')
        removed = [args for args in calls if args[:2] == ('image', 'rm')]
        self.assertEqual({args[-1] for args in removed}, {'branchline-skills:' + self.identifier, 'branchline-labracore:' + self.identifier})
        self.assertTrue(all(args[2] == '--no-prune' for args in removed))

    def test_rejects_wrong_identity_and_symlink_targets(self):
        for changed in [{'BRANCHLINE_PREVIEW_DIR': '/'}, {'BRANCHLINE_PREVIEW_ID': '../escape'}, {'COMPOSE_PROJECT_NAME': 'another-project'}]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                cleanup.cleanup({**self.environ, **changed})
        (self.directory / 'build-core').symlink_to(self.root, target_is_directory=True)
        with patch.object(cleanup, 'docker', return_value=''), patch.object(cleanup, 'mountpoints', return_value=[]), self.assertRaises(ValueError):
            cleanup.cleanup(self.environ)

    def test_refuses_owned_containers_foreign_mounts_and_nested_mounts(self):
        with patch.object(cleanup, 'docker', return_value='container-id'), self.assertRaises(RuntimeError):
            cleanup.cleanup(self.environ)
        with patch.object(cleanup, 'docker', side_effect=['', 'foreign-id', json.dumps([{'Source': str(self.directory / 'build-skills')}])]), self.assertRaises(RuntimeError):
            cleanup.cleanup(self.environ)
        with patch.object(cleanup, 'docker', return_value=''), patch.object(cleanup, 'mountpoints', return_value=[self.directory / 'build-skills/nested']), self.assertRaises(ValueError):
            cleanup.cleanup(self.environ)

    def test_corrupt_archive_prevents_database_deletion(self):
        (self.directory / 'mysql').mkdir()
        data = self.directory / 'mysql/data'
        data.write_text('database')
        cleanup.archive_preview(self.directory, self.identifier)
        (self.recovery / (self.identifier + '.tar.gz')).write_bytes(b'corrupt')
        with patch.object(cleanup, 'docker', return_value=''), patch.object(cleanup, 'mountpoints', return_value=[]), self.assertRaises(RuntimeError):
            cleanup.cleanup(self.environ)
        self.assertEqual(data.read_text(), 'database')

    def test_incomplete_archive_never_authorizes_deletion(self):
        (self.directory / 'mysql').mkdir()
        data = self.directory / 'mysql/data'
        data.write_text('database')
        self.recovery.mkdir()
        with tarfile.open(self.recovery / (self.identifier + '.tar.gz'), 'w:gz'):
            pass
        with patch.object(cleanup, 'docker', return_value=''), patch.object(cleanup, 'mountpoints', return_value=[]), self.assertRaises(RuntimeError):
            cleanup.cleanup(self.environ)
        self.assertEqual(data.read_text(), 'database')


if __name__ == '__main__':
    unittest.main()
