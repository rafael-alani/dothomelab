#!/usr/bin/env python3
"""Render only explicitly scoped staging secrets; never copy production env."""
import argparse
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from dotenv import parse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', type=Path, default=Path('/root/.env'))
    args = parser.parse_args()
    os.umask(0o077)
    env = dict(parse(args.env_file))
    directory = Path('/srv/appdata/docker/staging/film-introspect')
    directory.mkdir(exist_ok=True, parents=True)
    runtime = directory / 'runtime.env'
    old = dict(parse(runtime)) if runtime.exists() else {}
    key = 'STAGING_FILM_INTROSPECT_AUTH_SECRET'
    if not env.get(key):
        env[key] = old.get('BETTER_AUTH_SECRET') or secrets.token_hex(32)
        with args.env_file.open('a') as handle:
            handle.write(f'\n{key}={env[key]}\n')
    if len(env[key]) < 32:
        raise RuntimeError('Staging auth secret needs at least 32 characters')
    values = {
        'BETTER_AUTH_SECRET': env[key],
        'DEMO_MODE': env.get('STAGING_FILM_INTROSPECT_DEMO_MODE', 'true'),
    }
    for key in ('JELLYFIN_URL', 'JELLYFIN_API_KEY', 'JELLYFIN_USER_ID',
                'BAZARR_URL', 'BAZARR_API_KEY', 'OMDB_API_KEY'):
        values[key] = env.get('STAGING_FILM_INTROSPECT_' + key, '')
    if values['DEMO_MODE'] not in ('true', 'false'):
        raise RuntimeError('DEMO_MODE must be true or false')
    if any('\n' in value or '\r' in value for value in values.values()):
        raise RuntimeError('Multiline staging environment values are unsupported')
    temporary = runtime.with_suffix('.tmp')
    temporary.write_text(''.join(f'{key}={value}\n' for key, value in values.items()))
    os.chmod(temporary, 0o600)
    os.chown(temporary, 100000, 100000)
    os.replace(temporary, runtime)
    # Exact newly owned service directory only; no recursive ownership changes.
    os.chown(directory, 100000, 100000)
    os.chmod(directory, 0o700)
    print('Rendered scoped staging environment (values withheld)')


if __name__ == '__main__':
    main()
