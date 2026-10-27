import importlib.util
from pathlib import Path
import unittest
import tempfile

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).with_name('cleanup-runtime.py'))
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def test_reordered_mounts_are_safe_but_changed_mounts_are_not(self):
        mounts = [{'Source': '/data', 'Destination': '/db', 'RW': True},
                  {'Source': '/config', 'Destination': '/config', 'RW': False}]
        self.assertTrue(cleanup.same_mounts(mounts, list(reversed(mounts))))
        self.assertFalse(cleanup.same_mounts(mounts, mounts[:1]))
        for key, value in [('Source', '/other'), ('Destination', '/other'), ('RW', False)]:
            changed = [dict(m) for m in mounts]
            changed[0][key] = value
            self.assertFalse(cleanup.same_mounts(mounts, changed))

    def test_missing_readonly_git_config_requires_a_retained_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory)
            (archive / 'hosts').mkdir()
            (archive / 'hosts/old.yml').write_text('retained config')
            mount = {'Source': '/opt/dothomelab/hosts/old.yml', 'RW': False}
            self.assertEqual(cleanup.retained_bind(mount, archive), archive / 'hosts/old.yml')
            with self.assertRaises(ValueError):
                cleanup.retained_bind(mount)
            mount['RW'] = True
            with self.assertRaises(ValueError):
                cleanup.retained_bind(mount, archive)

    def test_only_consistently_exited_containers_are_removable(self):
        row = {'Name': '/restore_test', 'State': {'Status': 'exited', 'Running': False}, 'HostConfig': {}}
        cleanup.validate_target(row, 'exited')
        for listed, status, running in [('running', 'exited', False), ('exited', 'running', True),
                                        (None, 'exited', False), ('exited', 'exited', True)]:
            with self.subTest(listed=listed, status=status, running=running):
                row['State'].update(Status=status, Running=running)
                with self.assertRaises(ValueError):
                    cleanup.validate_target(row, listed)


if __name__ == '__main__':
    unittest.main()
