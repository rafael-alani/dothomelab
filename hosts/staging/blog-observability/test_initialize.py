#!/usr/bin/env python3
"""Isolated credential-preservation checks; no PVE files or network access."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


initialize = load('initialize_blog_secrets', 'initialize.py')
umami = load('initialize_blog_umami', 'initialize-umami.py')
SITE = json.loads(Path(__file__).with_name('website.json').read_text())
PASSWORD = 'a1' * 32


def http_error(status):
    body = {'error': {'code': 'incorrect-username-password' if status == 401 else 'unrelated-error'}}
    return urllib.error.HTTPError('http://fixture.invalid', status, 'fixture failure', {},
                                  io.BytesIO(json.dumps(body).encode()))


class UmamiInitializationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        env = root / 'runtime.env'
        env.write_text(f'BLOG_UMAMI_ADMIN_PASSWORD={PASSWORD}\n')
        (root / 'website.json').write_text(json.dumps(SITE))
        self.enterContext(patch.object(umami, 'ENV', env))
        self.enterContext(patch.object(umami, '__file__', str(root / 'initialize-umami.py')))
        self.output = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.enterContext(contextlib.redirect_stderr(self.output))
        self.requests = []

    def responses(self, values):
        pending = iter(values)

        def respond(request, **kwargs):
            self.requests.append((request.full_url.removeprefix(umami.BASE),
                                  json.loads(request.data) if request.data else None,
                                  request.get_header('Authorization')))
            value = next(pending)
            if isinstance(value, Exception):
                raise value
            return io.BytesIO(json.dumps(value).encode())

        self.enterContext(patch.object(umami.urllib.request, 'urlopen', side_effect=respond))

    def test_configured_account_is_never_reset(self):
        self.responses([{'token': 'configured-token'}, SITE])
        umami.main()
        self.assertEqual(self.requests, [
            ('/api/auth/login', {'username': 'admin', 'password': PASSWORD}, None),
            ('/api/websites/' + SITE['id'], None, 'Bearer configured-token'),
        ])
        for secret in (PASSWORD, 'configured-token'):
            self.assertNotIn(secret, self.output.getvalue())

    def test_seeded_account_rotates_reauthenticates_and_creates_absent_site(self):
        self.responses([http_error(401), {'token': 'seeded-token'}, {},
                        {'token': 'new-token'}, None, SITE])
        umami.main()
        self.assertEqual(self.requests, [
            ('/api/auth/login', {'username': 'admin', 'password': PASSWORD}, None),
            ('/api/auth/login', {'username': 'admin', 'password': 'umami'}, None),
            ('/api/me/password', {'currentPassword': 'umami', 'newPassword': PASSWORD},
             'Bearer seeded-token'),
            ('/api/auth/login', {'username': 'admin', 'password': PASSWORD}, None),
            ('/api/websites/' + SITE['id'], None, 'Bearer new-token'),
            ('/api/websites', SITE, 'Bearer new-token'),
        ])
        for secret in (PASSWORD, 'seeded-token', 'new-token'):
            self.assertNotIn(secret, self.output.getvalue())

    def test_unrelated_login_errors_do_not_attempt_seeded_login(self):
        for status in (400, 403, 500):
            with self.subTest(status=status):
                error = http_error(status)
                with patch.object(umami.urllib.request, 'urlopen', side_effect=error) as request:
                    with self.assertRaises(urllib.error.HTTPError):
                        umami.main()
                self.assertEqual(request.call_count, 1)

    def test_independently_managed_account_is_not_reset(self):
        self.responses([http_error(401), http_error(401)])
        with self.assertRaises(urllib.error.HTTPError):
            umami.main()
        self.assertEqual([request[0] for request in self.requests],
                         ['/api/auth/login', '/api/auth/login'])

    def test_site_identity_drift_fails_without_updating_it(self):
        for field in ('id', 'name', 'domain'):
            with self.subTest(field=field):
                self.requests.clear()
                self.responses([{'token': 'configured-token'}, {**SITE, field: 'different'}])
                with self.assertRaisesRegex(RuntimeError, 'identity differs'):
                    umami.main()
                self.assertEqual(len(self.requests), 2)
                self.assertIsNone(self.requests[-1][1])

    def test_site_authorization_failure_is_not_treated_as_absence(self):
        self.responses([{'token': 'configured-token'}, http_error(403)])
        with self.assertRaises(urllib.error.HTTPError):
            umami.main()
        self.assertEqual(len(self.requests), 2)


class SecretInitializationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.env = self.directory / 'operator.env'
        self.root = self.directory / 'appdata'
        self.values = {key: f'{index + 1:02x}' * 32 for index, key in enumerate(initialize.KEYS)}
        self.env.write_text('UNRELATED_KEY=private-fixture\n' + self.contents(self.values))
        self.enterContext(patch.object(initialize, 'ROOT', self.root))
        self.enterContext(patch.object(initialize, 'Path', side_effect=lambda value:
                                      self.env if str(value) == '/root/.env' else Path(value)))
        self.enterContext(patch.object(initialize.subprocess, 'check_output',
                                      return_value='rpool/appdata/docker\n'))
        self.enterContext(patch.object(initialize.os, 'chown'))
        self.enterContext(patch.object(initialize.os, 'umask'))
        self.enterContext(patch.object(initialize.secrets, 'token_hex', return_value='ff' * 32))
        self.output = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.enterContext(contextlib.redirect_stderr(self.output))

    @staticmethod
    def contents(values):
        return ''.join(f'{key}={value}\n' for key, value in values.items())

    def test_existing_operator_credentials_are_preserved_and_scoped(self):
        before = self.env.read_bytes()
        initialize.main()
        self.assertEqual(self.env.read_bytes(), before)
        runtime = self.root / 'runtime.env'
        self.assertEqual(dict(initialize.parse(runtime)), self.values)
        self.assertEqual(runtime.stat().st_mode & 0o777, 0o600)
        for secret in (*self.values.values(), 'private-fixture'):
            self.assertNotIn(secret, self.output.getvalue())
        self.assertNotIn('UNRELATED_KEY', runtime.read_text())

    def test_divergent_installed_credential_changes_neither_file(self):
        self.root.mkdir()
        runtime = self.root / 'runtime.env'
        runtime.write_text(self.contents({**self.values, initialize.KEYS[-1]: 'ee' * 32}))
        before = (self.env.read_bytes(), runtime.read_bytes())
        with self.assertRaisesRegex(RuntimeError, 'credential rotation is separate') as error:
            initialize.main()
        self.assertEqual((self.env.read_bytes(), runtime.read_bytes()), before)
        self.assertFalse((self.root / 'runtime.env.next').exists())
        self.assertNotIn('ee' * 32, str(error.exception) + self.output.getvalue())

    def test_invalid_secret_fails_without_writes_or_value_in_error(self):
        for invalid in ('short-private-fixture', 'nonhex-private-fixture-' * 3):
            with self.subTest(invalid_kind='short' if len(invalid) < 32 else 'nonhex'):
                self.env.write_text(self.contents({**self.values, initialize.KEYS[0]: invalid}))
                before = self.env.read_bytes()
                with self.assertRaisesRegex(RuntimeError, 'at least 32 hex characters') as error:
                    initialize.main()
                self.assertEqual(self.env.read_bytes(), before)
                self.assertFalse(self.root.exists())
                self.assertNotIn(invalid, str(error.exception) + self.output.getvalue())


if __name__ == '__main__':
    unittest.main()
