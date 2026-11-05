import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('access', Path(__file__).with_name('qbittorrent-access.py'))
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)


class AccessPolicy(unittest.TestCase):
    def test_current_policy_in_either_layout_needs_no_restart(self):
        for section, prefix in [('[Preferences]', 'WebUI\\'), ('[WebUI]', '')]:
            with self.subTest(section=section):
                text = section + '\n' + ''.join(prefix + key + '=' + value + '\n' for key, value in [
                    ('AuthSubnetWhitelist', '172.22.0.0/16'),
                    ('AuthSubnetWhitelistEnabled', 'true'), ('LocalHostAuth', 'true')])
                self.assertEqual(access.reconcile(text, '172.22.0.0/16'), text)

    def test_rebuild_changes_only_access_keys_in_active_section(self):
        text = ('[Preferences]\nWebUI\\AuthSubnetWhitelist=172.18.0.0/16\n'
                '[WebUI]\nAuthSubnetWhitelist=172.18.0.0/16\nPassword=test-only\n'
                '[Other]\nAuthSubnetWhitelist=untouched\n')
        result = access.reconcile(text, '172.22.0.0/16')
        self.assertIn('[WebUI]\nAuthSubnetWhitelistEnabled=true\nLocalHostAuth=true\nAuthSubnetWhitelist=172.22.0.0/16', result)
        self.assertIn('Password=test-only\n', result)
        self.assertIn('[Other]\nAuthSubnetWhitelist=untouched\n', result)
        self.assertIn('[Preferences]\nWebUI\\AuthSubnetWhitelist=172.18.0.0/16', result)
        self.assertEqual(access.reconcile(result, '172.22.0.0/16'), result)

    def test_unsafe_or_ambiguous_input_is_refused(self):
        for subnet in ['0.0.0.0/0', '172.16.0.0/12', '8.8.8.0/24', '::1/128']:
            with self.subTest(subnet=subnet), self.assertRaises(ValueError):
                access.reconcile('[WebUI]\n', subnet)
        for text in ['[Other]\n', '[WebUI]\n[WebUI]\n',
                     '[WebUI]\nLocalHostAuth=false\nLocalHostAuth=true\n']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                access.reconcile(text, '172.22.0.0/16')


if __name__ == '__main__':
    unittest.main()
