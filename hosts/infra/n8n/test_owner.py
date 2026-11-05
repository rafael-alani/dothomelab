import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('owner', Path(__file__).with_name('configure-owner.py'))
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


class OwnerRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'n8n.sqlite'
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE user (email TEXT,password TEXT,disabled INTEGER,roleSlug TEXT)')
            db.execute('INSERT INTO user VALUES (?,?,?,?)',
                       ('current@example.test', 'retained-test-hash', 0, 'global:owner'))

    def test_restore_preserves_changed_owner_without_old_credentials(self):
        with patch.dict('os.environ', {'N8N_DATABASE_PATH': str(self.database)}, clear=True), \
                patch('sys.argv', ['configure-owner.py', '--verify']), \
                patch.object(owner, 'request', return_value={'showSetupOnFirstLoad': False}) as request:
            self.assertEqual(owner.main(), 0)
            request.assert_called_once_with('/rest/settings')

    def test_missing_or_disabled_owner_fails(self):
        with sqlite3.connect(self.database) as db:
            db.execute('UPDATE user SET disabled=1')
        with self.assertRaises(RuntimeError):
            owner.verify_retained_owner(self.database)
        with sqlite3.connect(self.database) as db:
            db.execute('DELETE FROM user')
        with self.assertRaises(RuntimeError):
            owner.verify_retained_owner(self.database)

    def test_first_setup_creates_and_authenticates_seed_owner(self):
        env = {'N8N_ADMIN_EMAIL': 'seed@example.test', 'N8N_ADMIN_PASSWORD': 'test-only',
               'N8N_ADMIN_FIRST_NAME': 'Test', 'N8N_ADMIN_LAST_NAME': 'Owner'}
        with patch.dict('os.environ', env, clear=True), patch('sys.argv', ['configure-owner.py']), \
                patch.object(owner, 'request', side_effect=[{'showSetupOnFirstLoad': True}, {}, {}]) as request:
            self.assertEqual(owner.main(), 0)
            self.assertEqual([call.args[0] for call in request.call_args_list],
                             ['/rest/settings', '/rest/owner/setup', '/rest/login'])
            self.assertEqual(request.call_args_list[-1].args[1]['emailOrLdapLoginId'], env['N8N_ADMIN_EMAIL'])


if __name__ == '__main__':
    unittest.main()
