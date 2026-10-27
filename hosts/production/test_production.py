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

    def test_published_input_excludes_drafts_and_private_history(self):
        source = self.root / 'input'
        (source / 'published/interests').mkdir(parents=True)
        (source / 'published/interests/article.md').write_text('public')
        (source / 'preview').mkdir()
        (source / 'preview/private.md').write_text('secret draft')
        (source / 'manifest.json').write_text(json.dumps([{'id': 'public', 'status': 'published'}, {'id': 'private', 'status': 'draft'}]))
        (source / 'history.json').write_text(json.dumps({'public': {'current':'/public'}, 'private': {'current':'/private'}}))
        output = self.root / 'output'
        files = {str(p.relative_to(source)): __import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
        (source / 'checksums.json').write_text(json.dumps(files))
        revision = content.published_input(source, output)
        self.assertEqual(content.published_input(source, output), revision)
        self.assertFalse((output / revision / 'preview').exists())
        self.assertEqual(json.loads((output / revision / 'history.json').read_text()), {'public': {'current': '/public'}})
        self.assertEqual((source / 'published/interests/article.md').stat().st_ino, (output / revision / 'published/interests/article.md').stat().st_ino)

    def test_published_folder_rename_reaches_materialized_route_history(self):
        source = self.root / 'input'
        folder = source / 'published/interests/technical-write-ups'
        folder.mkdir(parents=True)
        identity = '6f20182b-397f-443f-adbf-3712de43f3f0'
        (folder / '_index.md').write_text(f'---\nid: {identity}\nslug: technical-write-ups\n---\n')
        (source / 'manifest.json').write_text(json.dumps([{'id': 'draft', 'status': 'draft'}]))
        renamed = {'current': '/technical-write-ups', 'paths': ['/technical-write-ups', '/work-and-nerdy']}
        (source / 'history.json').write_text(json.dumps({identity: renamed,
            'draft': {'current': '/private-draft', 'paths': ['/private-draft']},
            'retired': {'current': '/private-retired', 'paths': ['/private-retired']}}))
        base = self.root / 'base'
        (base / 'content').mkdir(parents=True)
        (base / 'content/route-history.json').write_text(json.dumps({identity:
            {'current': '/work-and-nerdy', 'paths': ['/work-and-nerdy']}}))
        output = self.root / 'output'
        files = {str(p.relative_to(source)): __import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
        (source / 'checksums.json').write_text(json.dumps(files))
        revision = content.published_input(source, output)
        self.assertEqual(json.loads((output / revision / 'history.json').read_text()), {identity: renamed})

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
