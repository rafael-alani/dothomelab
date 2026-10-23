#!/usr/bin/env python3
"""PVE: move the existing Umami/Grafana installation without upgrading images.

One-time migration, deliberately refusing an existing target. All rollback state
is retained; after routing changes, recovery is an operator decision so that new
analytics or dashboard edits cannot be silently discarded.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

OLD = Path('/srv/appdata/docker/staging/blog-observability')
NEW = Path('/srv/appdata/docker/blog-observability')
EXPECTED = '35fc0a46de2146bed03f63e70dd44c0f35811bc9'
CONTAINERS = ('blog-observability-umami-1', 'blog-observability-grafana-1', 'blog-umami-db')
COUNT_SQL = r"""SELECT format('SELECT %L, count(*) FROM %I.%I;',
tablename, schemaname, tablename) FROM pg_tables
WHERE schemaname='public' ORDER BY tablename;
\gexec
"""


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def guest(ctid, *args, **kwargs):
    return run('pct', 'exec', str(ctid), '--', *args, **kwargs)


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def counts(ctid):
    return guest(ctid, 'docker', 'exec', '-i', 'blog-umami-db', 'psql',
                 '-U', 'umami', '-d', 'umami', '-At', '-v', 'ON_ERROR_STOP=1',
                 input=COUNT_SQL, text=True, stdout=subprocess.PIPE).stdout


def checked_sqlite(path):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise RuntimeError('Grafana SQLite integrity failed')
        tables = [row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: db.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                for name in tables}


def main():
    if os.geteuid() != 0 or not shutil.which('pct'):
        raise RuntimeError('Run as root on PVE')
    repo = Path(output('git', 'rev-parse', '--show-toplevel'))
    if output('git', 'status', '--porcelain'):
        raise RuntimeError('Use a clean committed checkout')
    commit = output('git', 'rev-parse', 'HEAD')
    if output('pct', 'exec', '114', '--', 'cat', '/opt/dothomelab/DEPLOYED_COMMIT') != EXPECTED:
        raise RuntimeError('CT114 source changed; review the new revision first')
    if NEW.exists() or not (OLD / 'postgres/PG_VERSION').exists():
        raise RuntimeError('Requires original staging database and an absent Apps target')
    if output('findmnt', '-n', '-o', 'SOURCE', '-T', str(OLD)) != 'rpool/appdata/docker':
        raise RuntimeError('Canonical appdata mount is required')
    for name in CONTAINERS:
        if output('pct', 'exec', '114', '--', 'docker', 'inspect', '--format', '{{.State.Running}}', name) != 'true':
            raise RuntimeError('Source services must be running before migration')
    source_images = {name: output('pct', 'exec', '114', '--', 'docker', 'inspect',
                                 '--format', '{{.Image}}', name) for name in CONTAINERS}
    release = f'/opt/dothomelab-blog-observability/releases/{commit}'
    with tempfile.NamedTemporaryFile(prefix='observability-', suffix='.tar') as archive:
        run('git', 'archive', 'HEAD', stdout=archive)
        archive.flush()
        for ctid in (110, 112, 114):
            guest(ctid, 'install', '-d', '-m', '0755', release)
            guest_archive = '/run/observability-migration-source.tar'
            run('pct', 'push', str(ctid), archive.name, guest_archive, '--perms', '0600')
            guest(ctid, 'tar', '-xf', guest_archive, '-C', release)
            guest(ctid, 'rm', '-f', guest_archive)
            guest(ctid, 'sh', '-c', 'printf "%s\n" "$1" >"$2/DEPLOYED_COMMIT"', 'sh', commit, release)
    run('python3', str(repo / 'hosts/staging/blog-observability/initialize.py'))
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    rollback = NEW / ('rollback-' + stamp)
    rollback.mkdir(mode=0o700)
    os.chown(rollback, 100000, 100000)
    state = {'commit': commit, 'source_commit': EXPECTED, 'source_images': source_images,
             'phase': 'prepared', 'rollback': str(rollback)}

    def record(phase):
        state['phase'] = phase
        (rollback / 'migration.json').write_text(json.dumps(state, indent=2) + '\n')
        print('Migration phase: ' + phase, flush=True)

    compose = ('env', f'BLOG_OBSERVABILITY_COMMIT={commit}',
               'docker', 'compose', '--env-file', str(NEW / 'runtime.env'),
               '-f', release + '/hosts/apps/blog-observability/compose.yaml')
    guest(112, *compose, 'config', '--quiet')
    guest(112, *compose, 'pull')
    # Use the exact source image IDs, verified against the pinned target tags.
    images = guest(112, *compose, 'config', '--images', text=True, stdout=subprocess.PIPE).stdout.splitlines()
    target_ids = {output('pct', 'exec', '112', '--', 'docker', 'image', 'inspect', '--format', '{{.Id}}', image)
                  for image in images}
    if target_ids != set(source_images.values()):
        raise RuntimeError('Target images differ from the running source images')
    record('images-verified')
    cutover = False
    stopped = False
    try:
        stopped = True
        guest(114, 'docker', 'stop', '--time', '60', CONTAINERS[0], CONTAINERS[1])
        source_counts = counts(114)
        (rollback / 'postgres-counts.txt').write_text(source_counts)
        dump = rollback / 'umami.dump'
        with dump.open('wb') as handle:
            guest(114, 'docker', 'exec', 'blog-umami-db', 'pg_dump', '-U', 'umami', '-d', 'umami', '-Fc', stdout=handle)
        with dump.open('rb') as handle:
            guest(114, 'docker', 'exec', '-i', 'blog-umami-db', 'pg_restore', '--list', stdin=handle, stdout=subprocess.DEVNULL)
        guest(114, 'docker', 'stop', '--time', '60', 'blog-umami-db')
        with (rollback / 'SHA256SUMS').open('w') as handle:
            run('sha256sum', 'umami.dump', cwd=rollback, stdout=handle)
        source_grafana = checked_sqlite(OLD / 'grafana/grafana.db')
        if any((NEW / 'grafana').iterdir()):
            raise RuntimeError('Target Grafana directory is not empty')
        run('cp', '-a', str(OLD / 'grafana') + '/.', str(NEW / 'grafana') + '/')
        if checked_sqlite(NEW / 'grafana/grafana.db') != source_grafana:
            raise RuntimeError('Grafana table counts differ')
        (rollback / 'grafana-counts.json').write_text(json.dumps(source_grafana, indent=2) + '\n')
        record('sources-stopped-and-backed-up')
        guest(112, *compose, 'up', '-d', '--pull', 'never', '--wait', '--wait-timeout', '120', 'postgres')
        if counts(112).strip():
            raise RuntimeError('Target PostgreSQL public schema is not empty')
        with dump.open('rb') as handle:
            guest(112, 'docker', 'exec', '-i', 'blog-umami-db', 'pg_restore', '-U', 'umami', '-d', 'umami',
                  '--exit-on-error', '--no-owner', '--no-privileges', stdin=handle,
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if counts(112) != source_counts:
            raise RuntimeError('PostgreSQL table counts differ after restore')
        record('restored-and-counts-verified')
        guest(112, 'bash', release + '/hosts/apps/blog-observability/deploy.sh')
        guest(112, 'python3', release + '/hosts/staging/blog-observability/verify.py')
        # Backup the route database; never restore it wholesale over later edits.
        guest(110, 'python3', '-c', '''import sqlite3,sys
from pathlib import Path
p=Path('/srv/appdata/docker/infra-nginx-proxy-manager')
with sqlite3.connect(p/'data/database.sqlite') as a, sqlite3.connect(p/('database.sqlite.pre-observability-move-'+sys.argv[1])) as b:
 a.backup(b)
 assert b.execute('PRAGMA integrity_check').fetchone()==('ok',)
(p/('database.sqlite.pre-observability-move-'+sys.argv[1])).chmod(0o600)
print('NPM rollback integrity verified')
''', stamp)
        # From here new writes may reach CT112: no automatic data rollback.
        cutover = True
        record('switching-routes')
        guest(110, 'python3', release + '/hosts/staging/configure-routes.py',
              '--apps', release + '/hosts/staging/blog-observability/routes.json')
        for url in ('https://analytics.staging.rafael.media/api/heartbeat',
                    'https://grafana.staging.rafael.media/api/health'):
            guest(110, 'curl', '--fail', '--silent', '--show-error', '--output', '/dev/null', url)
        guest(112, 'ln', '-sfn', release, '/opt/dothomelab-blog-observability/current')
        run('install', '-m', '0755', str(repo / 'backup/pbs/blog-umami-database-backup.sh'),
            '/etc/dothomelab/backup-pre.d/70-blog-umami-database')
        run('bash', '/etc/dothomelab/backup-pre.d/70-blog-umami-database')
        # Retire only the three source containers; no volumes or data are deleted.
        guest(114, 'docker', 'rm', *CONTAINERS)
        retained = rollback / 'staging-state'
        retained.mkdir(mode=0o700)
        os.chown(retained, 100000, 100000)
        for name in ('postgres', 'grafana', 'runtime.env', 'backups'):
            (OLD / name).rename(retained / name)
        # Prevent the old deployment definition recreating the retired services.
        guest(114, 'flock', '-w', '60', '/srv/appdata/docker/staging/deploy.lock',
              'sh', '-eu', '-c', '''
test "$(cat /opt/dothomelab/DEPLOYED_COMMIT)" = "$1"
test ! -e "/opt/dothomelab.before-observability-move-$2"
cp -a "$3" "/opt/dothomelab.next-$2"
mv /opt/dothomelab "/opt/dothomelab.before-observability-move-$2"
mv "/opt/dothomelab.next-$2" /opt/dothomelab
''', 'sh', EXPECTED, commit, release)
        record('complete')
        print('Umami/Grafana moved to CT112; rollback retained at ' + str(rollback))
    except BaseException:
        if stopped and not cutover:
            try:
                guest(112, *compose, 'stop')
            finally:
                guest(114, 'docker', 'start', 'blog-umami-db', CONTAINERS[0], CONTAINERS[1])
                record('failed-before-cutover-source-restarted')
        raise


if __name__ == '__main__':
    os.umask(0o077)
    main()
