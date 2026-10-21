#!/usr/bin/env python3
"""No-network checks for the scoped Jellyfin account initializer."""
import contextlib
import importlib.util
import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('initialize_jellyfin', Path(__file__).with_name('initialize-meta-egg-jellyfin.py'))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

USER_ID = '1' * 32
FOLDER_ID = '22222222-2222-2222-2222-222222222222'


class InitializeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.env = Path(temporary.name) / '.env'
        self.env.write_text("# preserve this\nPRODUCTION_KEY='unrelated-fixture'\n")
        self.env.chmod(0o600)
        self.user = {'Name': setup.NAME, 'Id': USER_ID, 'Policy': {
            **dict.fromkeys(setup.DENIED, True), 'IsHidden': False,
            'AuthenticationProviderId': 'provider', 'PasswordResetProviderId': 'reset',
        }}

    def test_policy_is_movie_scoped_and_denies_write_control_and_transcoding(self):
        policy = setup.restricted_policy({**self.user['Policy'], 'FuturePermission': True}, [FOLDER_ID])
        self.assertTrue(all(policy[key] is False for key in setup.DENIED))
        self.assertFalse(policy['FuturePermission'])
        self.assertTrue(policy['IsHidden'])
        self.assertTrue(policy['EnableMediaPlayback'])
        self.assertEqual(policy['EnabledFolders'], [FOLDER_ID])
        self.assertEqual(policy['EnableContentDeletionFromFolders'], [])
        self.assertEqual(policy['SyncPlayAccess'], 'None')
        self.assertEqual(policy['AuthenticationProviderId'], 'provider')
        with self.assertRaises(setup.SetupError):
            setup.restricted_policy({}, [])

    def test_environment_preserves_other_values_and_rejects_unowned_keys(self):
        original = self.env.read_text()
        value = 'own-quoted"\\fixture'
        setup.write_env(self.env, {'PASSWORD': value, 'USER_ID': USER_ID})
        setup.write_env(self.env, {'USER_ID': USER_ID})
        self.assertTrue(self.env.read_text().startswith(original))
        self.assertEqual(dict(setup.parse(self.env))[setup.PREFIX + 'PASSWORD'], value)
        self.assertEqual(self.env.read_text().count(setup.PREFIX + 'USER_ID='), 1)
        self.assertEqual(self.env.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(setup.SetupError):
            setup.write_env(self.env, {'ADMIN_TOKEN': 'must-not-persist'})
        self.assertNotIn('must-not-persist', self.env.read_text())

    def test_existing_name_requires_saved_ownership_and_matching_identity(self):
        with patch.object(setup, 'request') as request:
            with self.assertRaisesRegex(setup.SetupError, 'refusing adoption'):
                setup.owned_token('http://jellyfin.test', self.user, {})
            with self.assertRaisesRegex(setup.SetupError, 'differs'):
                setup.owned_token('http://jellyfin.test', self.user, {'USER_ID': '3' * 32, 'PASSWORD': 'fixture'})
            request.assert_not_called()

    def test_lost_creation_response_recovers_without_adopting_or_rotating(self):
        created, calls = [], []
        def api(url, token, method, endpoint, payload=None):
            calls.append((method, endpoint))
            if endpoint == '/Library/VirtualFolders':
                return [{'ItemId': FOLDER_ID, 'CollectionType': 'movies'},
                        {'ItemId': '4' * 32, 'CollectionType': 'music'}]
            if endpoint == '/Users':
                return [self.user] if created else []
            if endpoint == '/Users/New':
                created.append(payload)
                raise setup.SetupError('Simulated lost creation response')
            if endpoint == '/Users/AuthenticateByName':
                self.assertEqual(payload['Pw'], created[0]['Password'])
                self.assertEqual(token, '')
                return {'User': self.user, 'AccessToken': 'restricted-user-token'}
            if endpoint.endswith('/Policy'):
                self.user['Policy'] = payload
                return None
            if endpoint in ('/Users/' + USER_ID, '/Users/Me'):
                return self.user
            self.fail('Unexpected endpoint')
        output = io.StringIO()
        with patch.object(setup, 'request', side_effect=api), contextlib.redirect_stdout(output):
            with self.assertRaisesRegex(setup.SetupError, 'lost creation'):
                setup.provision('http://jellyfin.test', 'admin-token-fixture', self.env)
            before = dict(setup.parse(self.env))
            self.assertTrue(before.get(setup.PREFIX + 'PASSWORD'))
            self.assertNotIn(setup.PREFIX + 'API_KEY', before)
            setup.provision('http://jellyfin.test', 'admin-token-fixture', self.env)
            setup.provision('http://jellyfin.test', 'admin-token-fixture', self.env)
        after = dict(setup.parse(self.env))
        self.assertEqual(before[setup.PREFIX + 'PASSWORD'], after[setup.PREFIX + 'PASSWORD'])
        self.assertEqual(after[setup.PREFIX + 'API_KEY'], 'restricted-user-token')
        self.assertNotIn('admin-token-fixture', self.env.read_text())
        self.assertEqual(calls.count(('POST', '/Users/New')), 1)
        self.assertEqual(calls.count(('POST', '/Users/AuthenticateByName')), 1)
        self.assertEqual(calls.count(('POST', '/Users/' + USER_ID + '/Policy')), 1)
        self.assertNotIn(created[0]['Password'], output.getvalue())
        self.assertNotIn('token', output.getvalue())

    def test_saved_credentials_cannot_be_retargeted_to_another_server(self):
        setup.write_env(self.env, {'URL': 'https://original.test', 'PASSWORD': 'retained-fixture'})
        with patch.object(setup, 'request') as request:
            with self.assertRaisesRegex(setup.SetupError, 'different server'):
                setup.provision('https://other.test', 'admin-fixture', self.env)
            request.assert_not_called()

    def test_redirects_and_response_details_are_withheld(self):
        self.assertIsNone(setup.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.test'))
        failure = urllib.error.HTTPError('https://other.test', 302, 'secret-response-fixture', {}, None)
        with patch.object(setup.urllib.request, 'build_opener') as factory:
            factory.return_value.open.side_effect = failure
            with self.assertRaises(setup.ApiError) as caught:
                setup.request('http://jellyfin.test', 'admin-token-fixture', 'GET', '/Users')
        self.assertEqual(caught.exception.status, 302)
        self.assertNotIn('fixture', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
