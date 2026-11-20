#!/usr/bin/env python3
"""Exercise client credential isolation, atomic files and accepted-release checks."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('configure_client', Path(__file__).with_name('configure-client.py'))
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class ConfigureClientTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.payload = {'cli': '#!/usr/bin/env node\nconsole.log("fixture")\n', 'token': 'fixture-token-' * 4}

    def write(self):
        return subprocess.run([sys.executable, '-c', client.WRITER], cwd=self.root,
                              input=json.dumps(self.payload).encode(), capture_output=True)

    def test_private_atomic_files_and_rerun_preserve_unrelated_data(self):
        (self.root / 'config').mkdir(mode=0o750)
        note = self.root / 'config/note'
        note.write_text('retain this')
        for token in ['first-fixture-' * 4, 'second-fixture-' * 4]:
            self.payload['token'] = token
            result = self.write()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout + result.stderr, b'')
            self.assertEqual((self.root / 'config/branchline-token').read_text(), token + '\n')
        self.assertEqual((self.root / 'bin/branchline').read_text(), self.payload['cli'])
        self.assertEqual((self.root / 'bin/branchline').stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / 'config/branchline-token').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'config').stat().st_mode & 0o777, 0o750)
        self.assertNotIn(self.payload['token'], (self.root / 'config/shell.env').read_text())
        self.assertEqual(note.read_text(), 'retain this')

    def test_refuses_symlink_directory_without_writing_outside_workspace(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'config').symlink_to(outside, target_is_directory=True)
        result = self.write()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertNotIn(self.payload['token'].encode(), result.stdout + result.stderr)

    def test_accepted_commit_and_vm_identity_are_required(self):
        vm = self.root / '116.conf'
        vm.write_text('name: codex-dev\n')
        sha = 'a' * 40
        (self.root / 'current.json').write_text(json.dumps({'commit': sha}))
        (self.root / 'runtime.env').write_text('UNRELATED=not-copied\nBRANCHLINE_TOKEN=' + self.payload['token'] + '\n')
        with patch.object(client, 'VM_CONFIG', vm), patch.object(client, 'BRANCHLINE', self.root):
            with patch.object(client, 'guest_git', side_effect=[(sha + '\n').encode(), self.payload['cli'].encode()]):
                actual_sha, payload = client.client_payload()
                self.assertEqual(actual_sha, sha)
                self.assertEqual(payload, self.payload)
            with patch.object(client, 'guest_git', return_value=('b' * 40).encode()):
                with self.assertRaisesRegex(RuntimeError, 'differs'):
                    client.client_payload()
            vm.write_text('name: another-workload\n')
            with patch.object(client, 'guest_git') as git:
                with self.assertRaisesRegex(RuntimeError, 'VM116'):
                    client.client_payload()
                git.assert_not_called()


if __name__ == '__main__':
    unittest.main()
