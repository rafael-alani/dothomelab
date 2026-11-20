#!/usr/bin/env python3
"""VM116: install accepted Branchline MCP and its dependency-aware execution worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request
import http.cookiejar

WORKSPACE = Path('/workspace')
POINTER = 'For Branchline planning, selections or implementation results, read /workspace/config/branchline/SKILL.md.'


def run(*args):
    return subprocess.check_output(args, text=True)


def write_private(target, content, mode=0o600):
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.is_symlink() or (target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid())):
        raise RuntimeError(f'Preserve unexpected destination: {target}')
    fd, temporary = tempfile.mkstemp(prefix='.' + target.name, dir=target.parent)
    with os.fdopen(fd, 'w') as handle:
        os.fchmod(handle.fileno(), mode)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def verify_release(release):
    commit = (release / 'SOURCE_COMMIT').read_text().strip()
    if not re.fullmatch('[0-9a-f]{40}', commit) or release.name != commit:
        raise RuntimeError('Release must be named by its committed source revision')
    manifest = json.loads((release / 'manifest.json').read_text())
    for name in ['mcp.mjs', 'worker.mjs', 'skills/branchline/SKILL.md']:
        source = release / name
        if source.is_symlink() or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != manifest.get(name):
            raise RuntimeError(f'Release integrity check failed: {name}')
    return commit


def check_idle(config):
    token = (WORKSPACE / 'config/branchline-token').read_text().strip()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = urllib.request.Request(config['url'] + '/api/session', data=json.dumps({'token': token}).encode(), headers={'Content-Type': 'application/json'})
    with opener.open(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError('Workspace authentication failed')
    with opener.open(config['url'] + '/api/plans', timeout=20) as response:
        catalog = json.load(response)
    for item in catalog['plans']:
        if item['status'] != 'submitted':
            continue
        with opener.open(config['url'] + '/api/plans/' + item['id'], timeout=20) as response:
            plan = json.load(response)
        if any(task.get('run', {}).get('status') == 'running' and task['run'].get('worker') == config['id'] for task in plan['tasks']):
            raise RuntimeError('Finish or cancel this worker\'s active tasks before replacing its runtime')


def install(release, dry_run=False):
    if os.getuid() != 1000 or WORKSPACE.resolve(strict=True) != WORKSPACE:
        raise RuntimeError('Run as codex (UID 1000) in VM116 with the canonical /workspace mounted')
    commit = verify_release(release)
    launcher = WORKSPACE / 'bin/branchline-mcp'
    servers = json.loads(run('/usr/local/bin/codex', 'mcp', 'list', '--json'))
    existing = next((server for server in servers if server['name'] == 'branchline'), None)
    if existing and existing['transport'].get('command') != str(launcher):
        raise RuntimeError('Preserve the unrelated MCP server named branchline')
    config_path = WORKSPACE / 'config/branchline-worker.json'
    config = json.loads(config_path.read_text()) if config_path.exists() else {
        'id': 'codex-dev', 'label': 'Codex on SSH VM',
        'url': 'https://branchline.staging.rafael.media',
        'tokenFile': '/workspace/config/branchline-token',
        'workspace': '/workspace/branchline-runs', 'concurrency': 2, 'maxTaskMs': 14400000,
        'command': ['/usr/local/bin/codex', 'exec', '--json', '--approve-for-me', '-c', 'mcp_servers.branchline.env_vars=["BRANCHLINE_RUN_CONTEXT"]', '--output-schema', '{schema}', '--cd', '{checkout}', '-'],
    }
    check_idle(config)
    if dry_run:
        print(f'Validated accepted integration release {commit}; MCP and worker can be installed.')
        return
    write_private(launcher, f'#!/usr/bin/env bash\nset -Eeuo pipefail\numask 077\n. /workspace/config/shell.env\nexec /usr/local/bin/node {release}/mcp.mjs\n', 0o700)
    write_private(WORKSPACE / 'bin/branchline-worker', f'#!/usr/bin/env bash\nset -Eeuo pipefail\numask 077\n. /workspace/config/shell.env\nexec /usr/local/bin/node {release}/worker.mjs /workspace/config/branchline-worker.json\n', 0o700)
    if not config_path.exists():
        write_private(config_path, json.dumps(config, indent=2) + '\n')
    write_private(WORKSPACE / 'config/branchline/SKILL.md', (release / 'skills/branchline/SKILL.md').read_text())
    codex_home = Path.home() / '.codex'
    if not existing:
        current = codex_home / 'config.toml'
        if current.exists():
            fd, backup = tempfile.mkstemp(prefix='config.before-branchline-', suffix='.toml', dir=codex_home)
            with os.fdopen(fd, 'wb') as handle:
                handle.write(current.read_bytes())
        run('/usr/local/bin/codex', 'mcp', 'add', 'branchline', '--', str(launcher))
    instructions = codex_home / 'AGENTS.md'
    content = instructions.read_text() if instructions.exists() else ''
    if POINTER not in content.splitlines():
        write_private(instructions, content + ('\n' if content and not content.endswith('\n') else '') + POINTER + '\n')
    unit = Path.home() / '.config/systemd/user/branchline-worker.service'
    write_private(unit, '''[Unit]
Description=Branchline implementation worker
After=network-online.target

[Service]
ExecStart=/workspace/bin/branchline-worker
WorkingDirectory=/workspace
Restart=on-failure
RestartSec=5
UMask=0077
KillMode=control-group
TimeoutStopSec=30
MemoryMax=6G
TasksMax=384

[Install]
WantedBy=default.target
''')
    run('systemctl', '--user', 'daemon-reload')
    run('systemctl', '--user', 'enable', 'branchline-worker.service')
    run('systemctl', '--user', 'restart', 'branchline-worker.service')
    write_private(WORKSPACE / 'config/branchline-integration-commit', commit + '\n')
    print(f'Installed Branchline MCP and worker from {commit}; account and other MCP configuration preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    install(args.release.resolve(strict=True), args.dry_run)
