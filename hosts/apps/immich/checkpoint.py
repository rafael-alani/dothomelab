#!/usr/bin/env python3
"""Capture a consistent Immich DB checkpoint and test its isolated restoration."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

ROOT = Path('/srv/appdata/docker/immich')
DATABASE = 'immich_migration_postgres'
COUNTS = r"""
SELECT format('SELECT json_build_array(%L, count(*))::text FROM %I.%I;',
              schemaname || '.' || tablename, schemaname, tablename)
FROM pg_tables WHERE schemaname NOT LIKE 'pg_%'
  AND schemaname <> 'information_schema' ORDER BY schemaname, tablename
\gexec
SELECT '"END"';
"""
EXTENSIONS = 'SELECT json_object_agg(extname, extversion ORDER BY extname) FROM pg_extension;'


def run(args, **kwargs):
    result = subprocess.run(args, stderr=subprocess.DEVNULL,
                            stdout=kwargs.pop('stdout', subprocess.PIPE), **kwargs)
    if result.returncode:
        # SQL/Docker diagnostics may contain recovery secrets or private data.
        raise RuntimeError(f'{args[0]} operation failed (exit {result.returncode})')
    return result.stdout


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def originals():
    inventory = {}
    for group in ('library', 'upload', 'profile'):
        root = ROOT / 'upload' / group
        if not root.is_dir() or root.is_symlink():
            raise ValueError('Missing or redirected original-media directory')
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise ValueError('Original-media symlink requires inspection')
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError('Unexpected original-media file type')
            before = path.stat()
            sha256 = digest(path)
            after = path.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError('Original media changed during hashing')
            inventory[str(path.relative_to(ROOT))] = dict(size=after.st_size, sha256=sha256)
    return inventory


def counts(lines):
    result = {}
    for line in lines:
        row = json.loads(line)
        if row == 'END':
            return result
        name, count = row
        if not isinstance(name, str) or name in result or type(count) is not int or count < 0:
            raise ValueError('Invalid database count inventory')
        result[name] = count
    raise ValueError('Database count inventory ended early')


def capture(label):
    if not re.fullmatch('[a-zA-Z0-9._-]+', label):
        raise ValueError('Invalid checkpoint label')
    target = ROOT / 'backups' / (stamp() + '-' + label)
    target.mkdir(parents=True, mode=0o700)
    print('Capturing checkpoint: ' + str(target), flush=True)
    images = {}
    for name in (DATABASE, 'immich_migration_server',
                 'immich_migration_machine_learning', 'immich_migration_redis'):
        row = inspect(name)
        if not row['State']['Running']:
            raise ValueError('An Immich dependency is not running')
        images[name] = dict(image=row['Image'], command=row['Config']['Cmd'],
                           digests=inspect(row['Image']).get('RepoDigests', []),
                           mounts=[dict(source=m['Source'], destination=m['Destination'],
                                        writable=m['RW']) for m in row['Mounts']])
    with urllib.request.urlopen('http://127.0.0.1:2283/api/server/version', timeout=10) as response:
        version = json.load(response)
    command = ['docker', 'exec', '-i', DATABASE, 'sh', '-ec',
               'exec psql -XqAt --set ON_ERROR_STOP=on --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"']
    session = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True)
    try:
        session.stdin.write('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\nSELECT pg_export_snapshot();\n')
        session.stdin.flush()
        snapshot = session.stdout.readline().strip()
        if not re.fullmatch('[0-9A-F]+-[0-9A-F]+-[0-9]+', snapshot):
            raise ValueError('Could not export a database snapshot')
        with (target / 'immich.dump').open('xb') as out:
            run(['docker', 'exec', DATABASE, 'sh', '-ec',
                 'exec pg_dump --format=custom --snapshot="$1" --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"',
                 'checkpoint', snapshot], stdout=out)
        session.stdin.write(COUNTS)
        session.stdin.flush()
        baseline = counts(session.stdout)
        session.stdin.write(EXTENSIONS + '\nSELECT json_build_array(current_database(), current_user);\n')
        session.stdin.flush()
        extensions = json.loads(session.stdout.readline())
        database, user = json.loads(session.stdout.readline())
        session.stdin.write('ROLLBACK;\n\\q\n')
        session.stdin.flush()
        if session.wait(timeout=30):
            raise ValueError('Snapshot session failed')
    finally:
        session.stdin.close()
        if session.poll() is None:
            session.terminate()
            session.wait(timeout=30)
        session.stdout.close()
    with (target / 'roles.sql').open('xb') as out:
        run(['docker', 'exec', DATABASE, 'sh', '-ec',
             'exec pg_dumpall --roles-only --username="$POSTGRES_USER"'], stdout=out)
    metadata = dict(format=1, version=version, images=images, database=database,
                    user=user, counts=baseline, extensions=extensions,
                    originals=originals(),
                    files={name: digest(target / name) for name in ('immich.dump', 'roles.sql')})
    (target / 'checkpoint.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(dict(checkpoint=str(target), tables=len(baseline),
                          assets=baseline.get('public.asset'), version=version)), flush=True)


def restore_test(target):
    target = target.resolve(strict=True)
    if not target.is_relative_to(ROOT) or target == ROOT:
        raise ValueError('Restore input must be inside canonical Immich appdata')
    metadata = json.loads((target / 'checkpoint.json').read_text())
    if metadata['format'] != 1 or set(metadata['files']) != {'immich.dump', 'roles.sql'}:
        raise ValueError('Unknown checkpoint format')
    for name, expected in metadata['files'].items():
        path = target / name
        if path.is_symlink() or digest(path) != expected:
            raise ValueError('Checkpoint checksum mismatch')
    if target.parent.name != 'backups' or target.parent.parent.name != 'immich':
        raise ValueError('Restore must preserve the checkpoint/media directory layout')
    media_root = target.parent.parent
    actual = {str(path.relative_to(media_root))
              for group in ('library', 'upload', 'profile')
              for path in (media_root / 'upload' / group).rglob('*') if not path.is_dir()}
    if actual != set(metadata['originals']):
        raise ValueError('Restored original-media inventory differs from the checkpoint')
    for name, expected in metadata['originals'].items():
        path = media_root / name
        if (not name.startswith(('upload/library/', 'upload/upload/', 'upload/profile/'))
                or not path.resolve().is_relative_to(media_root) or path.is_symlink()
                or path.stat().st_size != expected['size'] or digest(path) != expected['sha256']):
            raise ValueError('Original media missing or changed in restored backup')
    database, user = metadata['database'], metadata['user']
    image = metadata['images'][DATABASE]['image']
    if not re.fullmatch('sha256:[0-9a-f]{64}', image):
        raise ValueError('Checkpoint must pin an immutable database image')
    if inspect(image)['Id'] != image:
        raise ValueError('Matching database image is unavailable')
    identity = stamp().lower()
    container = 'immich_restore_check_' + identity
    data = ROOT / 'restore-tests' / identity
    data.mkdir(parents=True, mode=0o700)
    started = passed = False
    try:
        run(['docker', 'run', '-d', '--name', container, '--pull', 'never',
             '--network', 'none', '--label', 'dothomelab.restore-test=immich-checkpoint',
             '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', '-e', 'POSTGRES_DB=' + database,
             '-e', 'POSTGRES_USER=' + user, '-e', 'POSTGRES_INITDB_ARGS=--data-checksums',
             '-v', str(data) + ':/var/lib/postgresql/data', image,
             *(metadata['images'][DATABASE]['command'] or [])])
        started = True
        psql = ['docker', 'exec', '-i', container, 'psql', '-XqAt',
                '--set', 'ON_ERROR_STOP=on', '--dbname', database, '--username', user]
        for _ in range(90):
            try:
                if run(psql, input=b'SELECT 1;\n', timeout=10).strip() == b'1':
                    break
            except RuntimeError:
                pass
            time.sleep(1)
        else:
            raise ValueError('Isolated database did not become ready')
        with (target / 'immich.dump').open('rb') as source:
            run(['docker', 'exec', '-i', container, 'pg_restore', '--clean', '--if-exists',
                 '--exit-on-error', '--single-transaction', '--dbname', database,
                 '--username', user], stdin=source)
        restored = counts(run(psql, input=COUNTS.encode()).decode().splitlines())
        extensions = json.loads(run(psql, input=EXTENSIONS.encode()))
        if restored != metadata['counts'] or extensions != metadata['extensions']:
            raise ValueError('Restored table counts or extensions differ')
        run(['docker', 'stop', container])
        run(['docker', 'rm', container])
        passed = True
        evidence = dict(passed=True, tables=len(restored), assets=restored.get('public.asset'),
                        original_files=len(metadata['originals']),
                        image=image, data_path=str(data), removed_container=container)
        (target / ('restore-test-' + identity + '.json')).write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence), flush=True)
    finally:
        if started and not passed:
            subprocess.run(['docker', 'stop', container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print('Failed test retained for diagnosis: ' + container + '; data: ' + str(data), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('capture', 'test'))
    parser.add_argument('target', help='Checkpoint label for capture, directory for test')
    args = parser.parse_args()
    if os.geteuid() != 0 or ROOT.resolve() != ROOT or not os.path.ismount(ROOT.parent):
        raise ValueError('Run as root in CT112 with canonical appdata mounted')
    os.umask(0o077)
    if args.command == 'capture':
        capture(args.target)
    else:
        restore_test(Path(args.target))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit('Immich checkpoint failed (' + type(error).__name__ +
                         '); no private database diagnostics printed') from None
