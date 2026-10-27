#!/usr/bin/env python3
"""Guest-local cleanup of explicitly named stopped containers and disposable build cache."""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def inspect(name):
    return json.loads(run('docker', 'inspect', '--type', 'container', name))[0]


def validate_target(row, listed_state):
    if (row['State']['Status'] != 'exited' or row['State']['Running']
            or row['State'].get('Paused') or listed_state != 'exited'):
        raise ValueError('Target is not consistently stopped: ' + row['Name'])
    if row['HostConfig'].get('AutoRemove'):
        raise ValueError('Auto-removing container is not a retained cleanup target')


def retained_bind(mount, source_archive=None):
    source = Path(mount['Source'])
    if source.exists():
        return source
    if source_archive and not mount['RW']:
        # Migrations can move Git-owned configuration while preserving its source archive.
        relative = source.relative_to('/opt/dothomelab')
        archived = source_archive / relative
        if archived.is_file():
            return archived
    raise ValueError('A retained bind mount is missing')


def verify_inputs(rows, source_archive=None):
    for row in rows:
        run('docker', 'image', 'inspect', row['Image'])
        for mount in row['Mounts']:
            if mount['Type'] == 'bind':
                retained_bind(mount, source_archive)
            if mount['Type'] == 'volume':
                run('docker', 'volume', 'inspect', mount['Name'])


def inventory():
    return [json.loads(line) for line in run('docker', 'ps', '-a', '--no-trunc',
                                          '--format', '{{json .}}').splitlines()]


def images():
    return set(run('docker', 'image', 'ls', '--no-trunc', '-q').splitlines())


def same_mounts(before, after):
    # Docker may reorder its mount map between inspect calls.
    return sorted(json.dumps(m, sort_keys=True) for m in before) == sorted(
        json.dumps(m, sort_keys=True) for m in after)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container', action='append', default=[], help='Exact stopped container name; repeatable')
    parser.add_argument('--prune-build-cache', action='store_true', help='Keep up to 5GB of unused default-builder cache on staging/production')
    parser.add_argument('--apply', action='store_true', help='Default is an inspection-only plan')
    parser.add_argument('--source-archive', type=Path, help='Retained Git archive for moved read-only /opt/dothomelab config')
    args = parser.parse_args()
    if (not args.container and not args.prune_build_cache) or any(
            not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', name) for name in args.container):
        parser.error('Specify exact container names and/or build-cache cleanup')
    host = run('hostname', '-s')
    if os.geteuid() != 0 or host not in {'apps', 'staging', 'production'}:
        parser.error('Run as root through pct exec in Apps, Staging or Production')
    if args.prune_build_cache and host == 'apps':
        parser.error('Build-cache cleanup is limited to staging/production')
    if args.source_archive and (not args.source_archive.is_absolute()
                               or not (args.source_archive / 'DEPLOYED_COMMIT').is_file()):
        parser.error('Source archive must be an absolute retained guest archive with DEPLOYED_COMMIT')
    root = Path('/srv/appdata/docker')
    if host != 'apps':
        root /= host
    if not os.path.ismount(root):
        raise ValueError('Canonical appdata must be mounted')
    os.umask(0o077)
    with ExitStack() as stack:
        paths = [Path('/run/lock/dothomelab-runtime-cleanup.lock')]
        if host != 'apps':
            paths.append(root / 'deploy.lock')
        for path in paths:
            lock = stack.enter_context(path.open('a'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = inventory()
        states = {r['Names']: r['State'] for r in before}
        rows = [inspect(name) for name in dict.fromkeys(args.container)]
        for row in rows:
            validate_target(row, states.get(row['Name'].lstrip('/')))
        verify_inputs(rows, args.source_archive)
        print(json.dumps({'host': host, 'containers': [r['Name'].lstrip('/') for r in rows],
                          'build_cache_limit': '5GB' if args.prune_build_cache else None,
                          'apply': args.apply}), flush=True)
        if not args.apply:
            return
        saved_images = images()
        retained = {r['ID']: r['Names'] for r in before if r['State'] == 'running'}
        archive = root / 'runtime-cleanup' / (time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + str(os.getpid()))
        archive.mkdir(mode=0o700, parents=True)
        # Inspect includes credentials. Keep this recovery material only in protected appdata.
        payload = json.dumps(rows, indent=2) + '\n'
        (archive / 'containers.json').write_text(payload)
        (archive / 'SHA256SUMS').write_text(hashlib.sha256(payload.encode()).hexdigest() + '  containers.json\n')
        if args.source_archive:
            (archive / 'source-archive.txt').write_text(str(args.source_archive) + '\n')
        if json.loads((archive / 'containers.json').read_text()) != rows:
            raise ValueError('Recovery metadata did not round-trip')
        for row in rows:
            current = inspect(row['Id'])
            listed = {r['ID']: r['State'] for r in inventory()}
            validate_target(current, listed.get(row['Id']))
            if not same_mounts(current['Mounts'], row['Mounts']) or current['Image'] != row['Image']:
                raise ValueError('Target changed after inspection')
            run('docker', 'rm', row['Id'])  # Deliberately no force, volumes, images or networks.
            print('Removed stopped container: ' + row['Name'].lstrip('/'), flush=True)
        if args.prune_build_cache:
            output = run('docker', 'buildx', 'prune', '--builder', 'default', '--all',
                         '--force', '--max-used-space', '5GB')
            (archive / 'build-cache-result.txt').write_text(output + '\n')
            print('Build cache: ' + output.splitlines()[-1], flush=True)
        verify_inputs(rows, args.source_archive)
        after = inventory()
        assert retained.items() <= {r['ID']: r['Names'] for r in after if r['State'] == 'running'}.items(), 'A running container changed'
        assert not ({r['Id'] for r in rows} & {r['ID'] for r in after}), 'A removed container remains'
        assert saved_images <= images(), 'A retained image disappeared'
        print('Verified running containers, images and mounted data retained. Recovery metadata: ' + str(archive))


if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, OSError, ValueError, AssertionError) as error:
        # Command output and Docker configuration may contain credentials.
        raise SystemExit('Runtime cleanup failed: ' + type(error).__name__ + '; inspect protected recovery material') from None
