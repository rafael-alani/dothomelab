import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('source', Path(__file__).with_name('disable-enterprise-source.py'))
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
BASE = 'Types: deb\nURIs: https://enterprise.proxmox.com/debian/pbs\nSuites: trixie\nComponents: pbs-enterprise\n'


class SourceTests(unittest.TestCase):
    def test_disables_idempotently(self):
        for text in (BASE, BASE + 'Enabled: yes\n', BASE + 'Enabled: no\n'):
            changed = source.disable(text)
            self.assertEqual(changed.count('Enabled: no'), 1)
            self.assertEqual(source.disable(changed), changed)

    def test_refuses_other_or_mixed_repository(self):
        for text in (BASE.replace('/pbs', '/pve'), BASE + BASE):
            with self.assertRaises(ValueError):
                source.disable(text)


if __name__ == '__main__':
    unittest.main()
