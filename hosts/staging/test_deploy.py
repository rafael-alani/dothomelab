#!/usr/bin/env python3
"""Exercise SQLite generation isolation and failed/interrupted rollbacks."""
import importlib.util
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('deploy', Path(__file__).with_name('deploy.py'))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app_root = self.root / 'test'
        self.app_root.mkdir()
        self.app = {'repository': 'https://github.com/example/test.git', 'branch': 'staging',
                    'compose': 'compose.yaml', 'sqlite': ['test.db'], 'port': 8080,
                    'hostname': 'test.example', 'containers': 2}
        self.old = {'commit': 'a' * 40, 'configuration': 'a' * 12,
                    'release': '1-' + 'a' * 12 + '-' + 'a' * 12}
        self.release = deploy.release_path(self.app_root, self.old)
        self.data = self.release / 'data'
        self.data.mkdir(parents=True)
        with closing(sqlite3.connect(self.data / 'test.db')) as db, db:
            db.execute('CREATE TABLE notes (text TEXT)')
            db.execute('INSERT INTO notes VALUES (?)', ('preserve me',))
        deploy.write_json(self.app_root / 'current.json', self.old)
        (self.app_root / 'runtime.env').write_text('DEMO_MODE=true\n')
        (self.root / 'compose.yaml').write_text('services: {}\n')
        self.calls = []
        self.addCleanup(patch.stopall)
        patch.object(deploy, 'ROOT', self.root).start()
        patch.object(deploy, 'CACHE', self.root / 'cache').start()
        patch.object(deploy, 'HERE', self.root).start()
        patch.object(deploy, 'ensure_source').start()
        self.start_saved = patch.object(deploy, 'start_saved').start()
        patch.object(deploy, 'run', return_value='b' * 40).start()

    def assert_old_data(self):
        with closing(sqlite3.connect(self.data / 'test.db')) as db, db:
            self.assertEqual(db.execute('SELECT text FROM notes').fetchall(), [('preserve me',)])

    def test_independent_sqlite_generation(self):
        target = self.release / 'copied'
        deploy.copy_data(self.data, target, ['test.db'])
        with closing(sqlite3.connect(target / 'test.db')) as db, db:
            db.execute('UPDATE notes SET text = ?', ('new revision',))
        self.assert_old_data()

    def test_corrupt_database_fails_closed(self):
        (self.data / 'test.db').write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            deploy.copy_data(self.data, self.release / 'copied', ['test.db'])
        self.assertFalse((self.release / 'copied').exists())

    def test_symlink_data_rejected(self):
        (self.data / 'link').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(RuntimeError, 'symlinks'):
            deploy.copy_data(self.data, self.release / 'copied', ['test.db'])

    def test_build_failure_does_not_stop_current(self):
        def compose(release, *args):
            self.calls.append(args)
            if args[0] == 'build':
                raise RuntimeError('build failed')
        with patch.object(deploy, 'compose', side_effect=compose), patch.object(deploy, 'health'):
            with self.assertRaisesRegex(RuntimeError, 'build failed'):
                deploy.deploy('test', self.app, False)
        self.assertFalse(any(c[0] == 'stop' for c in self.calls))
        self.assertEqual(deploy.read_json(self.app_root / 'current.json'), self.old)
        self.assert_old_data()

    def test_bad_release_restores_previous_without_touching_old_database(self):
        def compose(release, *args):
            if args[0] == 'up':
                with closing(sqlite3.connect(release / 'data/test.db')) as db, db:
                    db.execute('UPDATE notes SET text = ?', ('broken migration',))
        with patch.object(deploy, 'compose', side_effect=compose), \
             patch.object(deploy, 'health', side_effect=[None, RuntimeError('bad health')]):
            with self.assertRaisesRegex(RuntimeError, 'bad health'):
                deploy.deploy('test', self.app, False)
        self.start_saved.assert_called_once_with('test', self.app_root, self.app, self.old)
        self.assertEqual(deploy.read_json(self.app_root / 'current.json'), self.old)
        self.assertTrue((self.app_root / 'failed.json').exists())
        self.assertFalse((self.app_root / 'pending.json').exists())
        self.assert_old_data()

    def test_interrupted_before_commit_restores_previous(self):
        candidate = {**self.old, 'release': '2-' + 'b' * 12 + '-' + 'b' * 12}
        deploy.write_json(self.app_root / 'pending.json', {'candidate': candidate, 'previous': self.old})
        with patch.object(deploy, 'compose'):
            deploy.recover('test', self.app_root, self.app)
        self.start_saved.assert_called_once()
        self.assert_old_data()

    def test_interrupted_after_commit_keeps_accepted_release(self):
        deploy.write_json(self.app_root / 'pending.json', {'candidate': self.old, 'previous': {}})
        with patch.object(deploy, 'compose') as compose:
            deploy.recover('test', self.app_root, self.app)
        compose.assert_not_called()
        self.start_saved.assert_not_called()


if __name__ == '__main__':
    unittest.main()
