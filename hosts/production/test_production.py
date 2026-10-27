#!/usr/bin/env python3
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

release = module('production_release', HERE / 'release.py')
content = module('production_content', HERE / 'prepare-content.py')
monitor = module('production_monitor', HERE / 'observability/configure.py')
pulse = module('production_pulse', HERE.parent / 'infra/pulse/configure-monitoring.py')


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(release, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_non_main_declaration_is_rejected(self):
        with patch.object(release, 'read', return_value={'blog': {'branch': 'staging', 'activation': 'explicit-user-request'}}):
            with self.assertRaisesRegex(RuntimeError, 'requires main'):
                release.app()

    def test_scaffold_guard_ignores_unrelated_commits_but_rejects_runtime_drift(self):
        repo = self.root / 'repo'
        repo.mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), '-c', 'core.hooksPath=/dev/null',
                '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', *args], text=True).strip()
        def save(name, value):
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        git('init', '--quiet')
        save('hosts/production/blog/compose.yaml', 'original')
        save('hosts/staging/editorial.py', 'original')
        git('add', '.')
        git('commit', '--quiet', '-m', 'Installed scaffold')
        installed = git('rev-parse', 'HEAD')
        binary = self.root / 'bin'
        binary.mkdir()
        pct = binary / 'pct'
        pct.write_text('#!/bin/sh\nprintf "%s\\n" "$FIXTURE_DEPLOYED_COMMIT"\n')
        pct.chmod(0o755)
        env = {**os.environ, 'PATH': str(binary) + os.pathsep + os.environ['PATH'],
               'FIXTURE_DEPLOYED_COMMIT': installed}
        def check():
            return subprocess.run(['bash', str(HERE / 'check-scaffold.sh'), str(repo)],
                                  env=env, capture_output=True, text=True)
        self.assertEqual(check().returncode, 0)
        save('docs/status.md', 'new evidence')
        save('hosts/infra/blog-publisher/export.mjs', 'unrelated publisher change')
        git('add', '.')
        git('commit', '--quiet', '-m', 'Unrelated work after scaffold installation')
        result = check()
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in ('hosts/production/blog/compose.yaml', 'hosts/staging/editorial.py'):
            with self.subTest(path=path):
                save(path, 'changed')
                self.assertNotEqual(check().returncode, 0)
                git('add', path)
                git('commit', '--quiet', '-m', 'Runtime drift')
                self.assertNotEqual(check().returncode, 0)
                save(path, 'original')
                git('add', path)
                git('commit', '--quiet', '-m', 'Restore runtime')
        env['FIXTURE_DEPLOYED_COMMIT'] = 'f' * 40
        self.assertNotEqual(check().returncode, 0)

    def test_pulse_enrolls_empty_guest_without_unrelated_container_requirements(self):
        client = Mock()
        client.request.return_value = [{'type': 'pve', 'name': 'afa', 'status': 'online'}]
        resources = {'system-container': [{'proxmox': {'vmid': 115}}],
                     'agent': [{'docker': {'hostname': 'production'}}], 'app-container': []}
        def run(*args):
            return 'VMID Status Name\n115 running production\n' if args == ('pct', 'list') else ''
        with patch.object(pulse, 'run', side_effect=run), \
             patch.object(pulse, 'resource_rows', side_effect=lambda client, kind: resources[kind]), \
             patch.object(pulse.time, 'sleep', side_effect=AssertionError('Empty guest should converge')):
            pulse.wait_for_resources(client, [115], {115: 'production'})

    def test_missing_main_never_uses_cached_main_or_staging(self):
        git = self.root / 'git'
        git.mkdir()
        for name in ('id_ed25519', 'known_hosts'):
            (git / name).write_text('fixture')
            (git / name).chmod(0o600)
        with patch.object(release, 'CACHE', self.root / 'cache'), patch.object(release, 'run') as run, \
             patch.object(release.subprocess, 'run') as command:
            command.return_value.returncode = 1
            with self.assertRaisesRegex(RuntimeError, 'Cannot fetch origin/main'):
                release.fetch()
            self.assertIn('+refs/heads/main:refs/heads/main', command.call_args.args[0])
            self.assertFalse(any('rev-parse' in call.args for call in run.call_args_list))

    def test_moved_main_prevents_any_container_change(self):
        release.write(self.root / 'prepared.json', {'commit': 'old'})
        with patch.object(release, 'dependencies'), patch.object(release, 'fetch', return_value=(None, 'new')), \
             patch.object(release, 'compose') as compose:
            with self.assertRaisesRegex(RuntimeError, 'changed after preparation'):
                release.activate()
            compose.assert_not_called()

    def test_failed_health_restores_previous_release(self):
        previous = {'release': '1-' + 'a'*12, 'commit': 'a'*40}
        candidate = {'release': '2-' + 'b'*12, 'commit': 'b'*40}
        release.write(self.root / 'prepared.json', candidate)
        release.write(self.root / 'current.json', previous)
        with patch.object(release, 'dependencies'), patch.object(release, 'fetch', return_value=(None, candidate['commit'])), \
             patch.object(release, 'compose') as compose, patch.object(release, 'health', side_effect=[RuntimeError('unhealthy'), None]):
            with self.assertRaisesRegex(RuntimeError, 'unhealthy'):
                release.activate()
            self.assertIn(((candidate, 'stop'), {}), compose.call_args_list)
            self.assertTrue(any(call.args[:2] == (previous, 'up') for call in compose.call_args_list))
        self.assertEqual(release.read(self.root / 'current.json'), previous)
        self.assertFalse((self.root / 'pending.json').exists())

    def test_interrupted_activation_does_not_overwrite_journal(self):
        release.write(self.root / 'prepared.json', {'commit': 'same'})
        release.write(self.root / 'pending.json', {'keep': True})
        with patch.object(release, 'dependencies'), patch.object(release, 'fetch', return_value=(None, 'same')), \
             patch.object(release, 'compose') as compose:
            with self.assertRaisesRegex(RuntimeError, 'Interrupted activation'):
                release.activate()
            compose.assert_not_called()
        self.assertEqual(release.read(self.root / 'pending.json'), {'keep': True})

    def test_published_input_excludes_drafts_and_private_history(self):
        source = self.root / 'input'
        (source / 'published/interests').mkdir(parents=True)
        (source / 'published/interests/article.md').write_text('public')
        (source / 'preview').mkdir()
        (source / 'preview/private.md').write_text('secret draft')
        (source / 'manifest.json').write_text(json.dumps([{'id': 'public', 'status': 'published'}, {'id': 'private', 'status': 'draft'}]))
        (source / 'history.json').write_text(json.dumps({'public': {'current':'/public'}, 'private': {'current':'/private'}}))
        output = self.root / 'output'
        revision = content.published_input(source, output)
        self.assertEqual(content.published_input(source, output), revision)
        self.assertFalse((output / revision / 'preview').exists())
        self.assertEqual(json.loads((output / revision / 'history.json').read_text()), {'public': {'current': '/public'}})
        release.editorial.snapshot(output, revision)

    def test_production_observations_are_isolated_and_initially_empty(self):
        self.assertTrue(all(not value for value in monitor.targets(False).values()))
        for value in monitor.targets(True).values():
            for group in value:
                self.assertEqual(group['labels']['environment'], 'production')
                self.assertEqual(group['labels']['project'], 'blog')
                self.assertFalse(any('staging' in target or '.114' in target for target in group['targets']))
        staging = json.loads((HERE.parent / 'staging/blog-observability/website.json').read_text())
        production = json.loads((HERE / 'observability/website.json').read_text())
        self.assertNotEqual(staging['id'], production['id'])
        dashboard = monitor.dashboard()
        for panel in dashboard['panels']:
            for target in panel.get('targets', []):
                expression = target['expr']
                self.assertNotIn('environment="staging"', expression)
                self.assertIn('environment="$environment"', expression)
        self.assertEqual(dashboard['templating']['list'][0]['current']['value'], 'production')

    def test_umami_null_for_missing_site_creates_only_production_identity(self):
        site = json.loads((HERE / 'observability/website.json').read_text())
        helper = {'parse': Mock(return_value={'BLOG_UMAMI_ADMIN_PASSWORD': 'fixture',
                                              'BLOG_GRAFANA_ADMIN_PASSWORD': 'fixture'}),
                  'ENV': self.root / 'fixture.env', 'login': Mock(return_value='fixture'),
                  'api': Mock(side_effect=[None, site])}
        with patch.object(monitor, 'helper', helper), \
             patch.object(monitor.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"status":"success"}')):
            monitor.accounts()
        self.assertEqual(helper['api'].call_args_list[-1].args, ('/api/websites', site, 'fixture'))


if __name__ == '__main__':
    unittest.main()
