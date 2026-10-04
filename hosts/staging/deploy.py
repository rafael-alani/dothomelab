#!/usr/bin/env python3
"""Deploy trusted staging branches; retain independent data for every release.

Only reviewed homelab Compose definitions run. Remote repositories supply build
contexts, never access to production appdata, the host environment, or sockets.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/srv/appdata/docker/staging')
CACHE = Path('/var/lib/dothomelab-staging')


def run(*args: str, capture: bool = False, timeout: int = 1200) -> str:
    result = subprocess.run(args, check=True, text=True, timeout=timeout,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ''


def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def write_json(path: Path, value: dict) -> None:
    temp = path.with_suffix('.tmp')
    with temp.open('w') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def registry() -> dict:
    apps = read_json(HERE / 'apps.json')
    ports: set[int] = set()
    for name, app in apps.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,48}', name):
            raise ValueError('Invalid staging application name')
        if not re.fullmatch(r'https://github.com/[\w.-]+/[\w.-]+\.git', app['repository']):
            raise ValueError('Only credential-free GitHub HTTPS repositories are supported')
        run('git', 'check-ref-format', 'refs/heads/' + app['branch'], capture=True)
        path = (HERE / app['compose']).resolve()
        if not path.is_relative_to(HERE) or not path.is_file():
            raise ValueError('Compose definition must be inside hosts/staging')
        for database in app['sqlite']:
            if not re.fullmatch(r'[\w-]+\.db', database):
                raise ValueError('SQLite paths must be simple filenames')
        if not 1024 <= app['port'] <= 65535 or app['port'] in ports:
            raise ValueError('Invalid or duplicate application port')
        ports.add(app['port'])
    return apps


def sqlite_check(path: Path) -> None:
    with closing(sqlite3.connect(f'file:{path}?mode=ro', uri=True)) as database:
        if database.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise RuntimeError(f'SQLite integrity check failed: {path.name}')


def copy_data(source: Path | None, target: Path, databases: list[str]) -> None:
    """Called after all old containers stop. Never modify the rollback tree."""
    if source:
        if any(p.is_symlink() for p in source.rglob('*')):
            raise RuntimeError('Refusing symlinks in staging data')
        required = sum(p.stat().st_size for p in source.rglob('*') if p.is_file())
        if shutil.disk_usage(target.parent).free < required + 1024**3:
            raise RuntimeError('Insufficient room for a separate data generation')
        for name in databases:
            if not (source / name).is_file():
                raise RuntimeError(f'Missing declared database: {name}')
            sqlite_check(source / name)
        shutil.copytree(source, target)
        for name in databases:
            sqlite_check(target / name)
    else:
        target.mkdir()


def release_path(app_root: Path, state: dict) -> Path:
    name = state['release']
    if not re.fullmatch(r'[0-9]+-[0-9a-f]{12}-[0-9a-f]{12}', name):
        raise ValueError('Invalid saved release identifier')
    return app_root / 'releases' / name


def compose(release: Path, *args: str) -> None:
    run('docker', 'compose', '--env-file', str(release / 'deploy.env'),
        '-f', str(release / 'compose.yaml'), *args)


def ensure_source(name: str, release: Path, sha: str) -> None:
    source = CACHE / name / sha
    if not (source / '.git').exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        run('git', 'clone', '--quiet', '--no-checkout', str(release / 'source.bundle'), str(source))
        run('git', '-C', str(source), 'checkout', '--quiet', '--detach', sha)
    if run('git', '-C', str(source), 'rev-parse', 'HEAD', capture=True) != sha:
        raise RuntimeError('Source commit mismatch')
    if run('git', '-C', str(source), 'status', '--porcelain', capture=True):
        raise RuntimeError('Refusing a modified staging build context')


def health(app: dict) -> None:
    base = f"http://192.168.0.114:{app['port']}"
    for path in ('/', '/api/health'):
        with urllib.request.urlopen(base + path, timeout=10) as response:
            body = response.read()
            if response.status != 200 or (path.endswith('health') and not json.loads(body).get('ok')):
                raise RuntimeError('Application HTTP health failed')


def verify(name: str, app: dict) -> None:
    app_root = ROOT / name
    state = read_json(app_root / 'current.json')
    if not state or (app_root / 'pending.json').exists():
        raise RuntimeError('No accepted release or a deployment is pending')
    release = release_path(app_root, state)
    compose(release, 'config', '--quiet')
    commits = run('docker', 'ps', '--filter', f'label=com.docker.compose.project=staging-{name}',
                  '--format', '{{.Label "dothomelab.staging.commit"}}', capture=True).splitlines()
    if commits != [state['commit']] * app['containers']:
        raise RuntimeError('Running container count or commit labels differ from accepted release')
    health(app)
    for database in app['sqlite']:
        sqlite_check(release / 'data' / database)
    print(f'{name}: verified {state["commit"]} and SQLite integrity')


def start_saved(name: str, app_root: Path, app: dict, state: dict) -> None:
    release = release_path(app_root, state)
    ensure_source(name, release, state['commit'])
    compose(release, 'config', '--quiet')
    images = run('docker', 'compose', '--env-file', str(release / 'deploy.env'),
                 '-f', str(release / 'compose.yaml'), 'config', '--images', capture=True).splitlines()
    missing = any(subprocess.run(['docker', 'image', 'inspect', image],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
                  for image in images)
    if missing:
        compose(release, 'build')
    compose(release, 'up', '-d', '--no-build', '--wait', '--wait-timeout', '120')
    health(app)


def recover(name: str, app_root: Path, app: dict) -> None:
    journal = app_root / 'pending.json'
    pending = read_json(journal)
    if not pending:
        return
    candidate = pending['candidate']
    current = read_json(app_root / 'current.json')
    if current.get('release') == candidate['release']:
        # Commit succeeded; process died before deleting the journal.
        journal.unlink()
        return
    compose(release_path(app_root, candidate), 'stop', '--timeout', '30')
    if pending['previous']:
        start_saved(name, app_root, app, pending['previous'])
    journal.unlink()
    print(f'{name}: recovered interrupted/failed deployment; candidate data retained', flush=True)


def deploy(name: str, app: dict, retry: bool) -> None:
    app_root = ROOT / name
    app_root.mkdir(parents=True, exist_ok=True)
    (app_root / 'releases').mkdir(exist_ok=True)
    if not (app_root / 'runtime.env').is_file():
        raise RuntimeError(f'{name}: scoped runtime.env is missing')
    recover(name, app_root, app)
    current = read_json(app_root / 'current.json')
    # Recovered appdata can start the accepted commit without contacting GitHub.
    # Only rebuild missing images, avoiding network work on normal timer polls.
    if current:
        release = release_path(app_root, current)
        try:
            health(app)
        except Exception:
            start_saved(name, app_root, app, current)

    mirror = CACHE / name / 'repository.git'
    if not mirror.exists():
        mirror.parent.mkdir(parents=True, exist_ok=True)
        run('git', 'init', '--quiet', '--bare', str(mirror))
    # A missing staging branch fails; it never silently deploys main.
    run('git', '--git-dir', str(mirror), 'fetch', '--quiet', app['repository'],
        '+refs/heads/' + app['branch'] + ':refs/heads/staging')
    sha = run('git', '--git-dir', str(mirror), 'rev-parse', 'refs/heads/staging', capture=True)
    template = (HERE / app['compose']).read_bytes()
    fingerprint = hashlib.sha256(template + (app_root / 'runtime.env').read_bytes()
                                 + json.dumps(app, sort_keys=True).encode()).hexdigest()[:12]
    desired = {'commit': sha, 'configuration': fingerprint}
    if all(current.get(k) == v for k, v in desired.items()):
        print(f'{name}: current {sha[:12]}', flush=True)
        return
    failed = read_json(app_root / 'failed.json')
    if not retry and all(failed.get(k) == v for k, v in desired.items()):
        raise RuntimeError(f'{name}: failed revision retained; push a fix or use --retry')

    candidate = {**desired, 'release': f'{time.time_ns()}-{sha[:12]}-{fingerprint}',
                 'repository': app['repository'], 'branch': app['branch']}
    release = release_path(app_root, candidate)
    release.mkdir()
    (release / 'compose.yaml').write_bytes(template)
    shutil.copyfile(app_root / 'runtime.env', release / 'runtime.env')
    run('git', '--git-dir', str(mirror), 'bundle', 'create', str(release / 'source.bundle'),
        'refs/heads/staging')
    ensure_source(name, release, sha)
    (release / 'deploy.env').write_text(
        f'STAGING_COMMIT={sha}\nSTAGING_IMAGE_TAG={sha}-{fingerprint}\n'
        f'STAGING_SOURCE={CACHE / name / sha}\nSTAGING_DATA={release / "data"}\n'
        f'STAGING_ENV={release / "runtime.env"}\n')
    write_json(release / 'release.json', candidate)
    try:
        compose(release, 'config', '--quiet')
        compose(release, 'build')
        write_json(app_root / 'pending.json', {'candidate': candidate, 'previous': current})
        if current:
            compose(release_path(app_root, current), 'stop', '--timeout', '30')
        copy_data(release_path(app_root, current) / 'data' if current else None,
                  release / 'data', app['sqlite'])
        compose(release, 'up', '-d', '--no-build', '--wait', '--wait-timeout', '120')
        health(app)
        for database in app['sqlite']:
            sqlite_check(release / 'data' / database)
        write_json(app_root / 'previous.json', current)
        write_json(app_root / 'current.json', candidate)
        (app_root / 'pending.json').unlink()
        (app_root / 'failed.json').unlink(missing_ok=True)
        print(f'{name}: accepted {sha} at https://{app["hostname"]}', flush=True)
    except BaseException:
        write_json(app_root / 'failed.json', candidate)
        recover(name, app_root, app)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app')
    parser.add_argument('--retry', action='store_true')
    parser.add_argument('--check', action='store_true', help='Validate registry only')
    parser.add_argument('--verify', action='store_true', help='Verify accepted live releases without Git/network updates')
    args = parser.parse_args()
    apps = registry()
    if args.check:
        print(f'Validated {len(apps)} staging application(s)')
        return 0
    if os.geteuid() != 0 or os.uname().nodename != 'staging':
        raise RuntimeError('Run as root inside staging CT114')
    if not os.path.ismount(ROOT):
        raise RuntimeError('Canonical staging appdata is not mounted')
    os.umask(0o077)
    CACHE.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'deploy.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another staging deployment is active')
            return 0
        selected = {args.app: apps[args.app]} if args.app else apps
        failures = 0
        for name, app in selected.items():
            try:
                if args.verify:
                    verify(name, app)
                else:
                    deploy(name, app, args.retry)
            except Exception as error:
                # Never dump command environments or application logs here.
                print(f'{name}: {type(error).__name__}: {error}', file=sys.stderr)
                failures += 1
        return int(failures > 0)


if __name__ == '__main__':
    raise SystemExit(main())
