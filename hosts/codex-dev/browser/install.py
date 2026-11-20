#!/usr/bin/env python3
"""Install the pinned browser MCP as the development account, preserving user state."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

POINTER = 'For preview or browser testing, read /workspace/config/browser.md.'


def run(*args):
    return subprocess.check_output(args, text=True)


def install(source, workspace, codex_home):
    launcher = workspace / 'bin/codex-browser'
    servers = json.loads(run('/usr/local/bin/codex', 'mcp', 'list', '--json'))
    existing = next((server for server in servers if server['name'] == 'playwright'), None)
    if existing and existing['transport'].get('command') != str(launcher):
        raise RuntimeError('An unrelated playwright MCP already exists; preserve it and resolve the name explicitly')

    lock = (source / 'package-lock.json').read_bytes()
    release = workspace / 'tools/playwright-mcp' / hashlib.sha256(lock).hexdigest()[:16]
    release.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Versioned installs leave running sessions and earlier tool releases intact.
    if not (release / '.installed').exists():
        for name in ('package.json', 'package-lock.json'):
            shutil.copyfile(source / name, release / name)
        run('/usr/local/bin/npm', 'ci', '--ignore-scripts', '--omit=dev', '--prefix', str(release))
        (release / '.installed').touch(mode=0o600)

    launcher.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    (workspace / 'browser-artifacts').mkdir(exist_ok=True, mode=0o700)
    launcher.write_text(f'''#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
artifacts=$(mktemp -d /workspace/browser-artifacts/session-XXXXXXXX)
exec /usr/local/bin/node {release}/node_modules/@playwright/mcp/cli.js \\
  --headless --executable-path /usr/bin/chromium --isolated \\
  --sandbox --caps vision --output-dir "$artifacts"
''')
    launcher.chmod(0o700)
    config_dir = workspace / 'config'
    config_dir.mkdir(exist_ok=True, mode=0o700)
    shutil.copyfile(source / 'browser.md', config_dir / 'browser.md')
    (config_dir / 'browser.md').chmod(0o600)

    codex_home.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not existing:
        config = codex_home / 'config.toml'
        if config.exists():
            fd, backup = tempfile.mkstemp(prefix='config.before-browser-', suffix='.toml', dir=codex_home)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(config.read_bytes())
        run('/usr/local/bin/codex', 'mcp', 'add', 'playwright', '--', str(launcher))
    instructions = codex_home / 'AGENTS.md'
    content = instructions.read_text() if instructions.exists() else ''
    if POINTER not in content.splitlines():
        with instructions.open('a') as stream:
            stream.write(('\n' if content and not content.endswith('\n') else '') + POINTER + '\n')
    instructions.chmod(0o600)
    print('Installed pinned Playwright MCP; user authentication and other MCP entries preserved.')


if __name__ == '__main__':
    if os.geteuid() == 0:
        raise SystemExit('Run as codex on VM116, not as root')
    os.umask(0o077)
    install(Path(__file__).resolve().parent, Path('/workspace'), Path.home() / '.codex')
