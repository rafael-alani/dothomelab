#!/usr/bin/env python3
"""Runtime install/downgrade tests using isolated files and a fake Docker boundary."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime', PROJECT / 'backup-runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.project = self.repo / 'hosts/infra/obsidian-sync'
        self.project.mkdir(parents=True)
        for name in runtime.FILES:
            shutil.copyfile(PROJECT / name, self.project / name)
        self.installed = self.root / 'installed'
        self.runner = self.root / 'runner'
        self.image = 'sha256:' + 'a' * 64
        self.revision = 'b' * 40
        self.image_hashes = '\n'.join(
            runtime.digest(self.project / name) + '  /usr/local/bin/' + target
            for name, target in [('proton-backup.sh', 'proton-backup'),
                                 ('proton-entrypoint.sh', 'proton-entrypoint'),
                                 ('source-verification.py', 'source-verification.py')])
        self.commands = []
        patch = mock.patch.object(runtime, 'run', side_effect=self.docker)
        patch.start()
        self.addCleanup(patch.stop)

    def docker(self, *args):
        self.commands.append(args)
        if args[1:3] == ('image', 'inspect'):
            return self.image
        if args[1] == 'run':
            return self.image_hashes
        if args[1] == 'compose' and args[-2:] == ('config', '--quiet'):
            return ''
        raise AssertionError(args)

    def install(self):
        return runtime.install(self.project, self.revision, self.installed, self.runner)

    def test_install_pins_image_and_survives_shared_checkout_downgrade(self):
        receipt = self.install()
        release = (self.installed / 'current').resolve()
        self.assertEqual(receipt['image_id'], self.image)
        self.assertEqual(self.runner.resolve(), release / 'backup-runner.sh')
        self.assertIn('image: ' + self.image, (release / 'compose.yaml').read_text())
        self.assertNotIn('build:', (release / 'compose.yaml').read_text())
        self.assertIn('pull_policy: never', (release / 'compose.yaml').read_text())
        compose = self.project / 'compose.yaml'
        compose.write_text(compose.read_text().replace('backup-v5', 'backup-v4'))
        (self.project / 'source-verification.py').unlink()
        with self.assertRaises(ValueError):
            runtime.check_repo(self.repo, self.installed)
        self.assertEqual(runtime.check_release(release)['backup_version'], 5)

    def test_reinstall_same_release_is_idempotent(self):
        self.install()
        self.install()
        self.assertEqual(len(list((self.installed / 'releases').iterdir())), 1)

    def test_wrong_image_contents_refuse_activation(self):
        self.image_hashes = self.image_hashes.replace(self.image_hashes[:64], '0' * 64)
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse((self.installed / 'current').exists())

    def test_tampered_installed_file_fails_readiness(self):
        self.install()
        release = (self.installed / 'current').resolve()
        (release / 'proton-backup.sh').write_text('old helper')
        with self.assertRaises(ValueError):
            runtime.check_release(release)

    def test_new_tag_with_old_helper_is_not_accepted(self):
        (self.project / 'proton-backup.sh').write_text('v4 without source checks')
        with self.assertRaises(ValueError):
            runtime.check_repo(self.repo, self.installed)

    def test_failed_candidate_keeps_previous_release(self):
        self.install()
        old = (self.installed / 'current').resolve()
        self.revision = 'c' * 40
        self.image_hashes = '0' * 64 + '  /usr/local/bin/proton-backup'
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual((self.installed / 'current').resolve(), old)


if __name__ == '__main__':
    unittest.main()
