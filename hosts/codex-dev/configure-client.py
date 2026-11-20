#!/usr/bin/env python3
"""PVE: install the accepted Branchline CLI and its scoped credential for VM116."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

WORKSPACE = Path('/srv/appdata/docker/codex-dev/workspace')
BRANCHLINE = Path('/srv/appdata/docker/staging/branchline')
VM_CONFIG = Path('/etc/pve/qemu-server/116.conf')

# Write as the workspace owner, never as PVE root inside VM-writable paths.
WRITER = r'''
import json, os, pathlib, stat, sys, tempfile
payload = json.load(sys.stdin)
workspace = pathlib.Path('.')
def directory(path):
    if path.is_symlink() or not path.is_dir() or path.stat().st_uid != os.getuid():
        raise RuntimeError('Client directory must belong to the development user')
    if path.stat().st_mode & 0o022:
        raise RuntimeError('Client directory must not be writable by other users')
directory(workspace)
for name in ['bin', 'config']:
    path = workspace / name
    path.mkdir(mode=0o700, exist_ok=True)
    directory(path)
files = [
    ('bin/branchline', payload['cli'], 0o700),
    ('config/branchline-token', payload['token'] + '\n', 0o600),
    ('config/shell.env', 'export PATH=/workspace/bin:$PATH\n'
        'export BRANCHLINE_URL=https://branchline.staging.rafael.media\n'
        'export BRANCHLINE_TOKEN_FILE=/workspace/config/branchline-token\n', 0o600),
]
for name, contents, mode in files:
    target = workspace / name
    if target.is_symlink() or (target.exists() and not stat.S_ISREG(target.stat().st_mode)):
        raise RuntimeError('Client destination must be a regular file')
    descriptor, temporary = tempfile.mkstemp(prefix='.' + target.name + '-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
'''


def guest_git(source, *args):
    result = subprocess.run(['pct', 'exec', '114', '--', 'git', '-C', str(source), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError('Cannot read the accepted Branchline source in CT114')
    return result.stdout


def client_payload():
    if not re.search(r'^name:\s*codex-dev\s*$', VM_CONFIG.read_text(), re.MULTILINE):
        raise RuntimeError('VM116 must exist and be named codex-dev')
    release = BRANCHLINE / 'current.json'
    sha = json.loads(release.read_text())['commit']
    if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RuntimeError('Accepted Branchline commit is invalid')
    source = Path('/var/lib/dothomelab-staging/branchline') / sha
    if guest_git(source, 'rev-parse', 'HEAD').decode().strip() != sha:
        raise RuntimeError('CT114 source differs from the accepted Branchline release')
    cli = guest_git(source, 'show', f'{sha}:scripts/branchline.js').decode()
    if not cli.startswith('#!/usr/bin/env node\n'):
        raise RuntimeError('Accepted Branchline CLI is missing its Node entrypoint')
    values = [line.removeprefix('BRANCHLINE_TOKEN=') for line in
              (BRANCHLINE / 'runtime.env').read_text().splitlines()
              if line.startswith('BRANCHLINE_TOKEN=')]
    if len(values) != 1 or len(values[0]) < 32 or values[0] != values[0].strip():
        raise RuntimeError('Scoped Branchline credential is missing or invalid')
    if json.loads(release.read_text())['commit'] != sha:
        raise RuntimeError('Branchline release changed during client preparation; retry')
    return sha, {'cli': cli, 'token': values[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if os.geteuid() or not Path('/etc/pve').is_dir():
        parser.error('Run on PVE as root')
    if WORKSPACE.resolve(strict=True) != WORKSPACE or not WORKSPACE.is_dir():
        raise RuntimeError('Expected the canonical VM116 workspace directory')
    sha, payload = client_payload()
    if args.dry_run:
        print(f'Validated accepted Branchline CLI {sha}; no client files changed')
        return
    result = subprocess.run(['setpriv', '--reuid=1000', '--regid=1000', '--clear-groups',
                             'python3', '-c', WRITER], input=json.dumps(payload).encode(),
                            cwd=WORKSPACE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError('Client file installation failed; inspect workspace ownership and destinations')
    print(f'Installed Branchline CLI {sha} and scoped VM116 configuration; credential withheld')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Client setup failed ({type(error).__name__}); no credential values logged', file=sys.stderr)
        raise SystemExit(1)
