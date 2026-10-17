#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from lifecycle import active_apps, retired

spec = importlib.util.spec_from_file_location('sync_homarr', Path(__file__).with_name('sync-homarr.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class RetirementTests(unittest.TestCase):
    def test_registry_and_dashboard_skip_retired_compose_and_symphony(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = root / 'symphony/control'
            control.mkdir(parents=True)
            (control / 'routes.json').write_text(json.dumps({'owner/old': {'hostname': 'old.staging.rafael.media', 'enabled': True}}))
            registry = {'old': {'repository': 'https://github.com/owner/old.git', 'hostname': 'old.staging.rafael.media'},
                        'keep': {'repository': 'https://github.com/owner/keep.git', 'hostname': 'keep.staging.rafael.media'}}
            path = root / 'apps.json'
            path.write_text(json.dumps(registry))
            retired_root = root / 'retired'
            retired_root.mkdir()
            marker = retired_root / (hashlib.sha256(b'owner/old').hexdigest() + '.json')
            marker.write_text(json.dumps({'version': 1, 'repository': 'owner/old', 'state': 'retiring'}))
            self.assertEqual(list(active_apps(path, retired_root)), ['keep'])
            self.assertEqual([app['key'] for app in sync.discover(registry, root)], ['compose:keep'])
            self.assertEqual(json.loads(path.read_text()), registry)
            marker.write_text('{}')
            with self.assertRaises(ValueError):
                retired('owner/old', retired_root)


if __name__ == '__main__':
    unittest.main()
