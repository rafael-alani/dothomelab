#!/usr/bin/env python3
"""Verify screening initialization cannot leak unrelated production credentials."""
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('initialize_env', Path(__file__).with_name('initialize-env.py'))
initialize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initialize)


class ScreeningEnvironmentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = self.root / 'input.env'
        self.env.write_text(
            'JELLYFIN_API_KEY=production-fixture\n'
            'OPENSUBTITLES_API_KEY=production-subtitles-fixture\n'
            'STAGING_STILLROOM_IMMICH_API_KEY=unrelated-fixture\n'
            'STAGING_META_EGG_JELLYFIN_URL=https://jellyfin.example\n'
            'STAGING_META_EGG_JELLYFIN_API_KEY=scoped-fixture\n'
            'STAGING_META_EGG_JELLYFIN_USER_ID=screening-user\n'
            'STAGING_META_EGG_OPENSUBTITLES_API_KEY=scoped-subtitles-fixture\n'
            'STAGING_FILM_INTROSPECT_AUTH_SECRET=' + 'x' * 64 + '\n'
        )
        self.addCleanup(patch.stopall)
        patch.object(initialize.os, 'chown').start()
        patch.object(initialize.os, 'umask').start()
        patch.object(initialize, 'active_apps', return_value={'meta-egg': {}, 'film-introspect': {}, 'stillroom': {}}).start()
        patch.object(initialize, 'Path', side_effect=self.local_path).start()

    def local_path(self, value):
        path = Path(value)
        try:
            return self.root / path.relative_to('/srv/appdata/docker/staging')
        except ValueError:
            return path

    def initialize_app(self, name):
        output = io.StringIO()
        with patch.object(initialize.sys, 'argv', ['initialize-env.py', '--env-file', str(self.env), '--app', name]), contextlib.redirect_stdout(output):
            initialize.main()
        self.assertNotIn('fixture', output.getvalue())
        return self.root / name / 'runtime.env'

    def test_credentials_are_scoped_to_meta_egg_and_film_gets_only_its_endpoint(self):
        meta = self.initialize_app('meta-egg')
        self.assertEqual(dict(initialize.parse(meta)), {
            'JELLYFIN_URL': 'https://jellyfin.example',
            'JELLYFIN_API_KEY': 'scoped-fixture',
            'JELLYFIN_USER_ID': 'screening-user',
            'OPENSUBTITLES_API_KEY': 'scoped-subtitles-fixture',
        })
        self.assertFalse((self.root / 'film-introspect').exists())
        self.assertFalse((self.root / 'stillroom').exists())
        self.assertEqual(meta.stat().st_mode & 0o777, 0o600)
        film = self.initialize_app('film-introspect')
        values = dict(initialize.parse(film))
        self.assertEqual(values['META_EGG_URL'], 'http://192.168.0.114:8085')
        self.assertEqual(values['DEMO_MODE'], 'false')
        self.assertEqual(values['JELLYFIN_API_KEY'], '')
        self.assertNotIn('fixture', film.read_text())

    def test_missing_connection_stays_unconfigured(self):
        self.env.write_text('JELLYFIN_API_KEY=production-fixture\n')
        runtime = self.initialize_app('meta-egg')
        self.assertEqual(set(dict(initialize.parse(runtime)).values()), {''})

    def test_stillroom_can_connect_in_app_without_operator_key(self):
        self.env.write_text('IMMICH_API_KEY=unrelated-production-fixture\n')
        runtime = self.initialize_app('stillroom')
        values = dict(initialize.parse(runtime))
        self.assertEqual(values['IMMICH_API_KEY'], '')
        self.assertEqual(values['IMMICH_URL'], 'http://192.168.0.112:2283/api')
        self.assertNotIn('fixture', runtime.read_text())
        self.assertEqual(runtime.stat().st_mode & 0o777, 0o600)

    def test_stillroom_preserves_only_its_optional_migration_key(self):
        runtime = self.initialize_app('stillroom')
        self.assertEqual(dict(initialize.parse(runtime))['IMMICH_API_KEY'], 'unrelated-fixture')
        self.assertNotIn('production-fixture', runtime.read_text())

    def test_multiline_credential_is_rejected_before_writing(self):
        self.env.write_text('STAGING_META_EGG_JELLYFIN_API_KEY="first\\nsecond"\n')
        with self.assertRaisesRegex(RuntimeError, 'Multiline'):
            self.initialize_app('meta-egg')
        self.assertFalse((self.root / 'meta-egg').exists())


if __name__ == '__main__':
    unittest.main()
