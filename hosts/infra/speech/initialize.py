#!/usr/bin/env python3
"""PVE: initialize only speech service state; never rotate an existing key."""
import os
import secrets
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
from dotenv import parse


def main():
    root = Path('/srv/appdata/docker/speech')
    if os.geteuid() or subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '-T', str(root.parent)], text=True).strip() != 'rpool/appdata/docker':
        raise SystemExit('Run on PVE with canonical appdata mounted')
    os.umask(0o077)
    for path, uid in [(root, 100000), (root / 'models', 101000)]:
        if path.exists():
            if path.is_symlink() or not path.is_dir() or path.stat().st_uid != uid:
                raise SystemExit('Unexpected speech directory owner/type')
        else:
            path.mkdir(mode=0o750)
            os.chown(path, uid, uid)
    env_path = Path('/root/.env')
    env = dict(parse(env_path))
    installed = root / 'runtime.env'
    previous = dict(parse(installed)).get('SPEECH_API_KEY') if installed.exists() else None
    key = env.get('SPEECH_API_KEY') or previous or secrets.token_hex(32)
    if previous and key != previous:
        raise SystemExit('Speech key differs; rotation is a separate operation')
    if len(key) < 32 or not all(c in '0123456789abcdefABCDEF' for c in key):
        raise SystemExit('Speech key must contain at least 32 hexadecimal characters')
    if not env.get('SPEECH_API_KEY'):
        with env_path.open('a') as handle:
            handle.write('\n# Shared Infra speech API\nSPEECH_API_KEY=' + key + '\n')
    temporary = root / 'runtime.env.next'
    temporary.write_text('SPEECH_API_KEY=' + key + '\n')
    temporary.chmod(0o600)
    os.chown(temporary, 100000, 100000)
    temporary.replace(installed)
    print('Speech state initialized; credentials withheld')


if __name__ == '__main__':
    main()
