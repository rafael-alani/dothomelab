#!/usr/bin/env python3
"""Check browser setup preserves the account and isolates browser sessions."""
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('browser_install', SOURCE / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class BrowserInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name) / 'workspace'
        self.codex_home = self.workspace / 'codex-state'
        self.codex_home.mkdir(parents=True)
        self.servers = [{'name': 'existing-tool', 'transport': {'command': '/custom/tool'}}]
        self.calls = []

    def fake_run(self, *args):
        self.calls.append(args)
        if args[1:] == ('mcp', 'list', '--json'):
            return json.dumps(self.servers)
        if args[1:5] == ('mcp', 'add', 'playwright', '--'):
            self.servers.append({'name': 'playwright', 'transport': {'command': args[5]}})
            with (self.codex_home / 'config.toml').open('a') as stream:
                stream.write('\n[mcp_servers.playwright]\ncommand = ' + json.dumps(args[5]) + '\n')
        elif args[1:4] != ('ci', '--ignore-scripts', '--omit=dev'):
            raise AssertionError(f'Unexpected external command: {args}')
        return ''

    def install(self):
        with patch.object(installer, 'run', side_effect=self.fake_run), patch('builtins.print'):
            installer.install(SOURCE, self.workspace, self.codex_home)

    def test_rerun_preserves_config_authentication_and_user_guidance(self):
        config = self.codex_home / 'config.toml'
        original = 'model = "custom-model"\n[mcp_servers.existing-tool]\ncommand = "/custom/tool"\n'
        config.write_text(original)
        config.chmod(0o600)
        auth = self.codex_home / 'auth.json'
        auth.write_bytes(b'{"fixture": "keep-this-authentication"}\n')
        auth.chmod(0o600)
        instructions = self.codex_home / 'AGENTS.md'
        instructions.write_text('Keep my existing instructions.')

        self.install()
        self.assertTrue(config.read_text().startswith(original))
        self.assertEqual(auth.read_bytes(), b'{"fixture": "keep-this-authentication"}\n')
        self.assertEqual(instructions.read_text(),
                         'Keep my existing instructions.\n' + installer.POINTER + '\n')
        backups = list(self.codex_home.glob('config.before-browser-*.toml'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)

        with config.open('a') as stream:
            stream.write('# Keep this later customization.\n')
        with instructions.open('a') as stream:
            stream.write('Keep later guidance, too.\n')
        before = {path: path.read_bytes() for path in (config, auth, instructions)}
        self.install()
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(auth.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.codex_home.glob('config.before-browser-*.toml')), backups)
        self.assertEqual(sum(call[1] == 'ci' for call in self.calls), 1)
        self.assertEqual(sum(call[1:3] == ('mcp', 'add') for call in self.calls), 1)
        self.assertEqual(self.servers[0]['transport']['command'], '/custom/tool')

    def test_unrelated_playwright_registration_is_rejected_before_mutation(self):
        self.servers.append({'name': 'playwright', 'transport': {'command': '/custom/playwright'}})
        config = self.codex_home / 'config.toml'
        config.write_text('retain this exact file\n')
        before = {str(path.relative_to(self.workspace)): path.read_bytes()
                  for path in self.workspace.rglob('*') if path.is_file()}
        with self.assertRaisesRegex(RuntimeError, 'unrelated playwright'):
            self.install()
        self.assertEqual({str(path.relative_to(self.workspace)): path.read_bytes()
                          for path in self.workspace.rglob('*') if path.is_file()}, before)
        self.assertEqual(set(self.workspace.iterdir()), {self.codex_home})
        self.assertEqual(len(self.calls), 1)

    def test_launcher_uses_isolated_sandboxed_headless_browser_and_private_artifacts(self):
        self.install()
        launcher = self.workspace / 'bin/codex-browser'
        content = launcher.read_text()
        syntax = subprocess.run(['bash', '-n'], input=content, text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        args = shlex.split(content[content.index('exec '):].replace('\\\n', ''))
        for option in ('--headless', '--isolated', '--sandbox'):
            self.assertIn(option, args)
        self.assertEqual(args[args.index('--executable-path') + 1], '/usr/bin/chromium')
        self.assertEqual(args[args.index('--caps') + 1], 'vision')
        self.assertEqual(args[args.index('--output-dir') + 1], '$artifacts')
        self.assertIn('umask 077', content)
        self.assertIn('mktemp -d /workspace/browser-artifacts/session-', content)
        self.assertEqual(launcher.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.workspace / 'browser-artifacts').stat().st_mode & 0o777, 0o700)


if __name__ == '__main__':
    unittest.main()
