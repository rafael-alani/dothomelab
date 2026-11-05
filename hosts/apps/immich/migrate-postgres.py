#!/usr/bin/env python3
"""Restore an Immich checkpoint to a NEW isolated PostgreSQL 18 directory.

Does not change the live database, app containers, environment or Compose file.
Successful test containers are removed; failed containers are stopped and retained.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

import checkpoint as cp

IMAGE = 'dothomelab/immich-postgres:18.6-vchord1.1.1-pgvector0.8.5'
EXPECTED_EXTENSIONS = {'vchord': '1.1.1', 'vector': '0.8.5'}


def retained_toc(text):
    # pgvecto.rs is no longer used by Immich 3. Keep every data/index entry.
    return '\n'.join(line for line in text.splitlines() if not re.search(
        r'\b(?:EXTENSION - vectors|COMMENT - EXTENSION vectors|SCHEMA - vectors)(?: |$)', line)) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('destination', type=Path, help='New directory directly under canonical Immich appdata')
    args = parser.parse_args()
    os.umask(0o077)
    target = args.checkpoint.resolve(strict=True)
    destination = args.destination
    if (os.geteuid() != 0 or not os.path.ismount(cp.ROOT.parent)
            or target.parent != cp.ROOT / 'backups'
            or destination.parent != cp.ROOT or not re.fullmatch('postgres18-[a-z0-9-]+', destination.name)
            or destination.exists() or destination.is_symlink()):
        raise ValueError('Require canonical checkpoint and an absent, explicitly named PostgreSQL 18 destination')
    metadata = json.loads((target / 'checkpoint.json').read_text())
    if metadata['format'] != 1 or set(metadata['files']) != {'immich.dump', 'roles.sql'}:
        raise ValueError('Unknown checkpoint format')
    for name, expected in metadata['files'].items():
        if cp.digest(target / name) != expected:
            raise ValueError('Checkpoint checksum mismatch')
    if any(not name.startswith('public.') for name in metadata['counts']):
        raise ValueError('Non-public tables require separate migration review')
    if cp.originals() != metadata['originals']:
        raise ValueError('Managed originals changed after checkpoint')
    # Fail before omitting legacy extension DDL if anything outside that extension
    # still depends on its objects. No DROP/CASCADE is run on the live database.
    sql = """SELECT count(*) FROM pg_depend d
JOIN pg_depend member ON d.refobjid=member.objid AND d.refclassid=member.classid
JOIN pg_extension e ON member.refobjid=e.oid
WHERE e.extname='vectors' AND member.deptype='e' AND d.deptype='n'
AND NOT EXISTS (SELECT 1 FROM pg_depend own WHERE own.objid=d.objid
AND own.classid=d.classid AND own.refobjid=e.oid AND own.deptype='e');"""
    user, database = metadata['user'], metadata['database']
    psql = ['psql', '-XqAt', '--set', 'ON_ERROR_STOP=on', '--username', user, '--dbname', database]
    if cp.run(['docker', 'exec', '-i', cp.DATABASE, *psql], input=sql.encode()).strip() != b'0':
        raise ValueError('Legacy vectors extension still has external dependents')
    live = cp.inspect(cp.DATABASE)
    env = dict(value.split('=', 1) for value in live['Config']['Env'] if '=' in value)
    destination.mkdir(mode=0o700)
    evidence = destination / 'migration-evidence'
    evidence.mkdir(mode=0o700)
    private_env = evidence / 'database.env'
    private_env.write_text('\n'.join(f'{key}={env[key]}' for key in
                          ('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB')) +
                          '\nPOSTGRES_INITDB_ARGS=--data-checksums\n')
    if any('\n' in env[key] or '\r' in env[key] for key in ('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB')):
        raise ValueError('Multiline database settings require review')
    name = 'immich_pg18_test_' + cp.stamp().lower()
    started = passed = False
    try:
        cp.run(['docker', 'run', '-d', '--name', name, '--pull', 'never', '--network', 'none',
                '--label', 'dothomelab.restore-test=immich-pg18', '--env-file', str(private_env),
                '-v', str(destination) + ':/var/lib/postgresql', IMAGE])
        started = True
        command = ['docker', 'exec', '-i', name, *psql]
        for _ in range(90):
            try:
                if cp.run(command, input=b'SELECT 1;').strip() == b'1':
                    break
            except RuntimeError:
                pass
            time.sleep(1)
        else:
            raise ValueError('Isolated database did not become ready')
        cp.run(command, input=b'CREATE EXTENSION IF NOT EXISTS vchord CASCADE;')
        listing = cp.run(['docker', 'exec', '-i', name, 'pg_restore', '--list'],
                         input=(target / 'immich.dump').read_bytes()).decode()
        toc = evidence / 'restore.list'
        toc.write_text(retained_toc(listing))
        cp.run(['docker', 'cp', str(toc), name + ':/tmp/restore.list'])
        with (target / 'immich.dump').open('rb') as source, (evidence / 'restore-errors.log').open('wb') as errors:
            result = subprocess.run(['docker', 'exec', '-i', name, 'pg_restore', '--exit-on-error',
                                     '--single-transaction', '--use-list=/tmp/restore.list',
                                     '--username', user, '--dbname', database],
                                    stdin=source, stdout=subprocess.DEVNULL, stderr=errors)
        if result.returncode:
            raise ValueError('Restore failed; diagnostics retained privately')
        actual = cp.counts(cp.run(command, input=cp.COUNTS.encode()).decode().splitlines())
        extensions = json.loads(cp.run(command, input=cp.EXTENSIONS.encode()))
        if actual != metadata['counts']:
            raise ValueError('Restored table counts differ')
        if (any(extensions.get(key) != value for key, value in EXPECTED_EXTENSIONS.items())
                or set(extensions) != set(metadata['extensions']) - {'vectors'}):
            raise ValueError('Unexpected restored extension set')
        version = cp.run(command, input=b'SHOW server_version;').decode().strip()
        if not version.startswith('18.6 '):
            raise ValueError('Unexpected PostgreSQL patch')
        invalid = cp.run(command, input=b'SELECT count(*) FROM pg_index WHERE NOT indisvalid;').strip()
        if invalid != b'0':
            raise ValueError('Invalid restored indexes')
        cp.run(['docker', 'stop', name])
        cp.run(['docker', 'rm', name])
        passed = True
        receipt = dict(passed=True, checkpoint=str(target), destination=str(destination),
                       tables=len(actual), assets=actual.get('public.asset'), extensions=extensions,
                       version=version, image=cp.inspect(IMAGE)['Id'], removed_container=name)
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt), flush=True)
    finally:
        private_env.unlink(missing_ok=True)
        if started and not passed:
            subprocess.run(['docker', 'stop', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print('Failed isolated test retained: ' + name + '; ' + str(destination), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit('Immich PostgreSQL migration failed (' + type(error).__name__ +
                         '); inspect private migration evidence') from None
