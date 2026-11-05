#!/usr/bin/env python3
"""PVE: retain WUD's operator credential in dotenv and provision its local runner."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
from dotenv import parse


def ensure_password(path):
    values = dict(parse(path))
    password = values.get('WUD_ADMIN_PASSWORD')
    if not password:
        password = secrets.token_hex(32)
        with path.open('a') as handle:
            handle.write(f'\nWUD_ADMIN_PASSWORD={password}\n')
    if len(password) < 32 or any(c in password for c in '\r\n'):
        raise ValueError('WUD administrator password must be single-line and at least 32 characters')
    return password


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run on PVE as root')
    os.umask(0o077)
    password = ensure_password(Path('/root/.env'))
    subprocess.run(['pct', 'exec', '110', '--', 'install', '-d', '-m', '0700',
                    '/etc/dothomelab'], check=True)
    with tempfile.NamedTemporaryFile(mode='w', dir='/run', prefix='wud-auth-') as handle:
        json.dump({'username': 'dothomelab', 'password': password}, handle)
        handle.flush()
        subprocess.run(['pct', 'push', '110', handle.name, '/etc/dothomelab/wud-auth.json',
                        '--perms', '0600'], check=True)
    print('WUD operator authentication provisioned; values withheld')


if __name__ == '__main__':
    main()
