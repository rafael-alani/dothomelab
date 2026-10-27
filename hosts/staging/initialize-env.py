#!/usr/bin/env python3
"""Render only explicitly scoped staging secrets; never copy production env."""
import argparse
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from dotenv import parse


from lifecycle import active_apps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', type=Path, default=Path('/root/.env'))
    parser.add_argument('--app', choices=('blog', 'ff', 'film-introspect', 'meta-egg', 'stillroom'))
    args = parser.parse_args()
    apps = active_apps(Path(__file__).with_name('apps.json'))
    os.umask(0o077)
    if 'meta-egg' in apps and args.app in (None, 'meta-egg'):
        env = dict(parse(args.env_file))
        values = {key: env.get('STAGING_META_EGG_' + key, '')
                  for key in ('JELLYFIN_URL', 'JELLYFIN_API_KEY', 'JELLYFIN_USER_ID',
                              'OPENSUBTITLES_API_KEY')}
        if any('\n' in value or '\r' in value for value in values.values()):
            raise RuntimeError('Multiline staging values are unsupported')
        directory = Path('/srv/appdata/docker/staging/meta-egg')
        directory.mkdir(exist_ok=True, parents=True)
        temporary = directory / 'runtime.tmp'
        temporary.write_text(''.join(f'{key}={value}\n' for key, value in values.items()))
        os.chmod(temporary, 0o600)
        os.chown(temporary, 100000, 100000)
        os.replace(temporary, directory / 'runtime.env')
        os.chown(directory, 100000, 100000)
        os.chmod(directory, 0o700)
        print('Rendered dedicated Meta Egg connection (values withheld)')
    if args.app == 'meta-egg':
        return
    if 'stillroom' in apps and args.app in (None, 'stillroom'):
        env = dict(parse(args.env_file))
        key = env.get('STAGING_STILLROOM_IMMICH_API_KEY', '')
        # Optional migration input; personal connections are configured in-app.
        values = {'IMMICH_URL': env.get('STAGING_STILLROOM_IMMICH_URL', 'http://192.168.0.112:2283/api'),
                  'IMMICH_API_KEY': key}
        if any('\n' in value or '\r' in value for value in values.values()):
            raise RuntimeError('Multiline staging values are unsupported')
        directory = Path('/srv/appdata/docker/staging/stillroom')
        directory.mkdir(exist_ok=True, parents=True)
        temporary = directory / 'runtime.tmp'
        temporary.write_text(''.join(f'{key}={value}\n' for key, value in values.items()))
        os.chmod(temporary, 0o600)
        os.chown(temporary, 100000, 100000)
        os.replace(temporary, directory / 'runtime.env')
        os.chown(directory, 100000, 100000)
        os.chmod(directory, 0o700)
        print('Rendered dedicated Stillroom connection (values withheld)')
    if args.app == 'stillroom':
        return
    for name in ('blog', 'ff'):
        if name not in apps or args.app not in (None, name):
            continue
        # Stateless apps: an empty scoped file, never production integrations.
        directory = Path('/srv/appdata/docker/staging') / name
        directory.mkdir(exist_ok=True, parents=True)
        runtime = directory / 'runtime.env'
        temporary = runtime.with_suffix('.tmp')
        temporary.write_text('')
        os.chmod(temporary, 0o600)
        os.chown(temporary, 100000, 100000)
        os.replace(temporary, runtime)
        os.chown(directory, 100000, 100000)
        os.chmod(directory, 0o700)
        print(f'Rendered empty {name} staging environment')
    if args.app in ('blog', 'ff') or 'film-introspect' not in apps:
        print('Film-introspect environment unchanged (not selected, absent, or retired)')
        return
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
        'DEMO_MODE': env.get('STAGING_FILM_INTROSPECT_DEMO_MODE', 'false'),
        'META_EGG_URL': env.get('STAGING_FILM_INTROSPECT_META_EGG_URL', 'http://192.168.0.114:8085'),
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
