#!/usr/bin/env python3
"""PVE: generate an app-only read deploy key; registration is a separate GitHub step."""
import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True)
    parser.add_argument('--environment', choices=('staging', 'production'), default='staging')
    args = parser.parse_args()
    apps = json.loads((Path(__file__).resolve().parents[1] / args.environment / 'apps.json').read_text())
    if args.app not in apps or not apps[args.app].get('private'):
        parser.error('Choose a declared private repository')
    if os.geteuid() != 0 or not Path('/etc/pve').is_dir():
        parser.error('Run on PVE as root')
    root = Path('/srv/appdata/docker') / args.environment / args.app / 'git'
    os.umask(0o077)
    root.mkdir(exist_ok=True)
    if root.is_symlink():
        raise RuntimeError('Refusing a symlink credential directory')
    key = root / 'id_ed25519'
    if not key.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C',
                        args.app + '-' + args.environment + '-readonly', '-f', str(key)], check=True)
    public = key.with_suffix('.pub')
    if not public.is_file():
        raise RuntimeError('Existing deploy key lacks its public key; inspect privately')
    known = root / 'known_hosts'
    if not known.exists():
        # Authenticate host keys through GitHub's HTTPS API; never trust keyscan alone.
        with urllib.request.urlopen('https://api.github.com/meta', timeout=20) as response:
            keys = json.load(response)['ssh_keys']
        if not keys or any('\n' in value for value in keys):
            raise RuntimeError('Invalid GitHub host-key response')
        known.write_text(''.join('github.com ' + value + '\n' for value in keys))
    for path in (root, key, public, known):
        if path.is_symlink():
            raise RuntimeError('Refusing symlink credential paths')
        os.chown(path, 100000, 100000)
        os.chmod(path, 0o700 if path == root else 0o600)
    print('Register the public .pub file as a READ-ONLY deploy key for ' + apps[args.app]['repository'])
    print('Private key remains in canonical ' + args.environment + ' appdata; no application container mounts it')


if __name__ == '__main__':
    main()
