#!/usr/bin/env python3
"""CT115: explicit main-only static blog releases. No background deployment."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = Path('/srv/appdata/docker/production/blog')
CACHE = Path('/var/lib/dothomelab-production/blog')
sys.path.insert(0, str(HERE.parent / 'staging'))
import editorial


def run(*args, capture=False):
    result = subprocess.run(args, check=True, text=True, timeout=1800,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ''


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def write(path, data):
    temporary = path.with_suffix('.next')
    with temporary.open('w') as handle:
        json.dump(data, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def app():
    value = read(HERE / 'apps.json')['blog']
    if value['branch'] != 'main' or value['activation'] != 'explicit-user-request':
        raise RuntimeError('Production requires main and explicit activation')
    return value


def dependencies():
    missing = []
    for name, url in app()['dependencies'].items():
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status != 200:
                    raise RuntimeError('Unhealthy dependency')
        except Exception:
            missing.append(name)
    if missing:
        raise RuntimeError('Unavailable production dependencies: ' + ', '.join(missing) +
                           '; notify Rafael, do not provision replacements or use demo mode')
    print('Production dependencies reachable: ' + ', '.join(app()['dependencies']))


def fetch():
    key = ROOT / 'git/id_ed25519'
    known = key.with_name('known_hosts')
    if any(not p.is_file() or p.is_symlink() for p in (key, known)) or key.stat().st_mode & 0o077:
        raise RuntimeError('Production read-only deploy key or pinned host keys missing')
    CACHE.mkdir(parents=True, exist_ok=True)
    mirror = CACHE / 'repository.git'
    if not mirror.exists():
        run('git', 'init', '--bare', '--quiet', str(mirror))
    ssh = shlex.join(['ssh', '-i', str(key), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                     '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(known)])
    repository = app()['repository'].replace('https://github.com/', 'git@github.com:')
    result = subprocess.run(['git', '-c', 'core.sshCommand=' + ssh, '--git-dir', str(mirror),
                             'fetch', '--quiet', repository, '+refs/heads/main:refs/heads/main'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    if result.returncode:
        raise RuntimeError('Cannot fetch origin/main: confirm the branch exists and the production read-only deploy key is registered; staging is never a fallback')
    return mirror, run('git', '--git-dir', str(mirror), 'rev-parse', 'refs/heads/main', capture=True)


def release_path(state):
    name = state.get('release', '')
    if not re.fullmatch(r'[0-9]+-[0-9a-f]{12}', name):
        raise ValueError('Invalid production release identifier')
    result = ROOT / 'releases' / name
    if result.is_symlink():
        raise ValueError('Release must not be a symlink')
    return result


def compose(state, *args):
    release = release_path(state)
    run('docker', 'compose', '--env-file', str(release / 'deploy.env'),
        '-f', str(release / 'compose.yaml'), *args)


def prepare():
    dependencies()
    mirror, commit = fetch()
    if (ROOT / 'pending.json').exists():
        raise RuntimeError('Interrupted production activation exists; inspect pending.json and recover before preparing')
    release = ROOT / 'releases' / f'{time.time_ns()}-{commit[:12]}'
    release.mkdir(parents=True)
    bundle = release / 'source.bundle'
    run('git', '--git-dir', str(mirror), 'bundle', 'create', str(bundle), 'refs/heads/main')
    source = CACHE / release.name
    run('git', 'clone', '--quiet', str(bundle), str(source))
    run('git', '-C', str(source), 'checkout', '--quiet', '--detach', commit)
    if not (source / 'Dockerfile').is_file():
        raise RuntimeError('origin/main lacks the portable Docker contract; candidate retained without activation')
    current_content = read(ROOT / 'editorial/current.json')
    revision = current_content.get('revision')
    if not revision:
        raise RuntimeError('Published-only content input missing; prepare it on PVE first')
    exported = editorial.snapshot(ROOT / 'editorial', revision)
    shutil.copytree(exported, release / 'editorial' / revision)
    source = editorial.materialize(source, release / 'editorial' / revision,
                                   CACHE / (release.name + '-published'), 'published')
    shutil.copyfile(HERE / app()['compose'], release / 'compose.yaml')
    state = {'release': release.name, 'commit': commit, 'branch': 'main',
             'repository': app()['repository'], 'content': revision,
             'platform': (HERE.parents[1] / 'DEPLOYED_COMMIT').read_text().strip()}
    (release / 'deploy.env').write_text(f'PRODUCTION_SOURCE={source}\nPRODUCTION_IMAGE_TAG={release.name}\nPRODUCTION_COMMIT={commit}\n')
    write(release / 'release.json', state)
    compose(state, 'config', '--quiet')
    compose(state, 'build')
    # Exercise image configuration without starting a server or binding a port.
    run('docker', 'run', '--rm', '--network', 'none', '--read-only', '--tmpfs', '/tmp',
        '--entrypoint', 'nginx', 'dothomelab-production/blog:' + release.name, '-t')
    write(ROOT / 'prepared.json', state)
    print(f'Prepared origin/main {commit}; published content {revision}; no application started')


def health():
    for path in ('/', app()['health_path'], '/feed.xml', '/sitemap.xml'):
        with urllib.request.urlopen('http://192.168.0.115:8084' + path, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError('Production origin health failed')


def activate():
    dependencies()
    candidate = read(ROOT / 'prepared.json')
    if not candidate:
        raise RuntimeError('No prepared production release')
    _, head = fetch()
    if head != candidate['commit']:
        raise RuntimeError('origin/main changed after preparation; prepare and review it again')
    if (ROOT / 'pending.json').exists():
        raise RuntimeError('Interrupted activation requires inspection; refusing to replace its journal')
    previous = read(ROOT / 'current.json')
    compose(candidate, 'config', '--quiet')
    write(ROOT / 'pending.json', {'previous': previous, 'candidate': candidate})
    try:
        compose(candidate, 'up', '-d', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '120')
        health()
    except Exception:
        compose(candidate, 'stop')
        if previous:
            compose(previous, 'config', '--quiet')
            compose(previous, 'up', '-d', '--no-build', '--pull', 'never', '--wait')
            health()
        (ROOT / 'pending.json').unlink()
        raise
    write(ROOT / 'previous.json', previous)
    write(ROOT / 'current.json', candidate)
    (ROOT / 'pending.json').unlink()
    print(f'Production origin healthy at {candidate["commit"]}; public routing is a separate final step')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0 or run('hostname', '-s', capture=True) != 'production':
        parser.error('Run inside CT115 through pct exec')
    os.umask(0o077)
    with (ROOT.parent / 'deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.check:
            dependencies()
        elif args.prepare:
            prepare()
        else:
            activate()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None
