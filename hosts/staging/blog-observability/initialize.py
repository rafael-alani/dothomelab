#!/usr/bin/env python3
"""PVE only: create this stack's secrets and exact appdata directories."""
import os
import secrets
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
from dotenv import parse

ROOT = Path('/srv/appdata/docker/blog-observability')
STAGING_ROOT = Path('/srv/appdata/docker/staging/blog-observability')
KEYS = ('BLOG_UMAMI_DB_PASSWORD', 'BLOG_UMAMI_APP_SECRET',
        'BLOG_UMAMI_ADMIN_PASSWORD', 'BLOG_GRAFANA_ADMIN_PASSWORD')


def main():
    if subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '-T', str(ROOT.parent)], text=True).strip() != 'rpool/appdata/docker':
        raise RuntimeError('Canonical PVE appdata mount is required')
    os.umask(0o077)
    env_path = Path('/root/.env')
    env = dict(parse(env_path))
    installed = [dict(parse(path / 'runtime.env')) for path in (ROOT, STAGING_ROOT)
                 if (path / 'runtime.env').exists()]
    missing = {}
    for key in KEYS:
        values = {item[key] for item in installed if item.get(key)}
        if len(values) > 1 or (env.get(key) and values and env[key] not in values):
            raise RuntimeError(f'{key} differs from the installed value; credential rotation is separate')
        if not env.get(key):
            env[key] = next(iter(values), None) or secrets.token_hex(32)
            missing[key] = env[key]
        if len(env[key]) < 32 or not all(c in '0123456789abcdefABCDEF' for c in env[key]):
            raise RuntimeError(f'{key} must be at least 32 hex characters')
    if missing:
        with env_path.open('a') as handle:
            handle.write('\n# Blog observability (operator secrets)\n')
            handle.writelines(f'{key}={value}\n' for key, value in missing.items())
    # Both guests use the same unprivileged mapping. Never repair existing owners.
    paths = [(ROOT, 0), (ROOT / 'postgres', 70), (ROOT / 'grafana', 472),
             (ROOT / 'backups', 0), (STAGING_ROOT, 0), (STAGING_ROOT / 'alloy', 0)]
    for path, guest_uid in paths:
        if path.exists():
            if path.is_symlink() or path.stat().st_uid != 100000 + guest_uid:
                raise RuntimeError(f'Unexpected owner/type at {path}')
        else:
            path.mkdir(mode=0o750)
            os.chown(path, 100000 + guest_uid, 100000 + guest_uid)
    temporary = ROOT / 'runtime.env.next'
    temporary.write_text(''.join(f'{key}={env[key]}\n' for key in KEYS))
    os.chown(temporary, 100000, 100000)
    temporary.chmod(0o600)
    temporary.replace(ROOT / 'runtime.env')
    print('Apps observability secrets/appdata and staging collector state initialized; values withheld')


if __name__ == '__main__':
    main()
