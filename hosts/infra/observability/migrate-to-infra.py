#!/usr/bin/env python3
"""PVE: one-time CT112 -> CT110 migration, with verified retained rollback.

No image upgrades, volume deletion or production application release. Before
routing changes, failure stops the candidate and restarts the source. Afterwards
writes may have arrived: reconciliation is explicit, never a silent stale restore.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

OLD = Path('/srv/appdata/docker/blog-observability')
NEW = Path('/srv/appdata/docker/observability')
APPDATA = NEW.parent
SOURCE = ('blog-observability-umami-1', 'blog-observability-grafana-1', 'blog-umami-db', 'prometheus', 'loki')
EXPECTED = {110: '68cba604cac0f75b4dcf062dfaabaacbf4dfcedc',
            112: 'c2661ddd1d2ca2db757f911c05d3606934b2ccdb',
            114: '68cba604cac0f75b4dcf062dfaabaacbf4dfcedc',
            115: 'fc039780a6af6789258096a1aba17c71e176b24d'}
COUNT_SQL = """SELECT format('SELECT %L, count(*) FROM %I.%I;', tablename, schemaname, tablename)
FROM pg_tables WHERE schemaname='public' ORDER BY tablename;
\\gexec
"""


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def guest(ctid, *args, **kwargs):
    return run('pct', 'exec', str(ctid), '--', *args, **kwargs)


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def counts(ctid, name):
    return guest(ctid, 'docker', 'exec', '-i', name, 'psql', '-U', 'umami', '-d', 'umami',
                 '-At', '-v', 'ON_ERROR_STOP=1', input=COUNT_SQL, text=True, stdout=subprocess.PIPE).stdout


def digests(ctid, image):
    return set(json.loads(output('pct', 'exec', str(ctid), '--', 'docker', 'image', 'inspect',
                                 '--format', '{{json .RepoDigests}}', image)))


def promote(ctid, release, commit):
    # Source replacement only; application images and appdata are unchanged.
    args = ['sh', '-eu', '-c', '''
test "$(cat /opt/dothomelab/DEPLOYED_COMMIT)" = "$1"
test ! -e "/opt/dothomelab.before-shared-observability-$2"
cp -a "$3" "/opt/dothomelab.next-$2"
mv /opt/dothomelab "/opt/dothomelab.before-shared-observability-$2"
mv "/opt/dothomelab.next-$2" /opt/dothomelab
''', 'sh', EXPECTED[ctid], commit, release]
    if ctid == 114:
        args = ['flock', '-w', '60', '/srv/appdata/docker/staging/deploy.lock', *args]
    guest(ctid, *args)
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
        raise RuntimeError('Run on PVE as root')
    repo = Path(output('git', 'rev-parse', '--show-toplevel'))
    commit = output('git', 'rev-parse', 'HEAD')
    if output('git', 'status', '--porcelain'):
        raise RuntimeError('Use a clean committed checkout')
    for ctid, expected in EXPECTED.items():
        if output('pct', 'exec', str(ctid), '--', 'cat', '/opt/dothomelab/DEPLOYED_COMMIT') != expected:
            raise RuntimeError(f'CT{ctid} source changed; reconcile before migration')
    if not (OLD / 'postgres/PG_VERSION').is_file() or (NEW / 'postgres/PG_VERSION').exists():
        raise RuntimeError('Requires original database and an uninitialized target')
    for name in SOURCE:
        if output('pct', 'exec', '112', '--', 'docker', 'inspect', '--format', '{{.State.Running}}', name) != 'true':
            raise RuntimeError('All source services must be running')
    for name in ('blog-observability', 'prometheus', 'loki'):
        if output('findmnt', '-n', '-o', 'SOURCE', '-T', str(APPDATA / name)) != 'rpool/appdata/docker':
            raise RuntimeError('Canonical appdata mount required')
    run('bash', str(repo / 'hosts/infra/observability/install-source.sh'), '--archive-only')
    release = '/opt/dothomelab-observability/releases/' + commit
    archive = Path('/run/observability-source-' + commit + '.tar')
    with archive.open('wb') as stream:
        run('git', 'archive', 'HEAD', stdout=stream)
    for ctid in EXPECTED:
        guest(ctid, 'install', '-d', '-m', '0755', release)
        run('pct', 'push', str(ctid), str(archive), '/run/observability-source.tar', '--perms', '0600')
        guest(ctid, 'tar', '-xf', '/run/observability-source.tar', '-C', release)
        guest(ctid, 'sh', '-c', 'printf "%s\n" "$1" >"$2/DEPLOYED_COMMIT"', 'sh', commit, release)
        guest(ctid, 'rm', '/run/observability-source.tar')
    archive.unlink()
    run('python3', str(repo / 'hosts/infra/observability/initialize.py'))
    if any((NEW / 'grafana').iterdir()):
        raise RuntimeError('Target Grafana directory must be empty')
    shared = release + '/hosts/infra/observability'
    guest(110, 'bash', release + '/hosts/infra/prometheus/prepare.sh')
    guest(110, 'bash', release + '/hosts/infra/loki/prepare.sh')
    def compose(folder, *args):
        return guest(110, 'env', 'BLOG_OBSERVABILITY_COMMIT=' + commit, 'docker', 'compose',
                     '--env-file', str(NEW / 'runtime.env'), '-f', release + '/hosts/infra/' + folder + '/compose.yaml', *args)
    for folder in ('observability', 'prometheus', 'loki'):
        compose(folder, 'config', '--quiet')
        compose(folder, 'pull', '--quiet')
    for name, target in zip(SOURCE, ('ghcr.io/umami-software/umami:3.4.0', 'grafana/grafana:13.2.4',
                                   'postgres:17-alpine', 'prom/prometheus:v3.13.1', 'grafana/loki:3.7.3')):
        declared = [line.strip().split('image: ', 1)[1] for line in (repo / 'hosts/infra/observability/compose.yaml').read_text().splitlines() if line.strip().startswith('image: ')]
        target = next((image for image in declared if image.startswith(target + '@')), target)
        source_image = output('pct', 'exec', '112', '--', 'docker', 'inspect', '--format', '{{.Image}}', name)
        if not digests(112, source_image).intersection(digests(110, target)):
            raise RuntimeError('Image digest drift: ' + name)
    guest(110, 'bash', shared + '/validate.sh')
    rollback = NEW / ('rollback-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    rollback.mkdir(mode=0o700)
    state = {'commit': commit, 'sources': EXPECTED, 'rollback': str(rollback)}
    def record(phase):
        state['phase'] = phase
        (rollback / 'migration.json').write_text(json.dumps(state, indent=2) + '\n')
        print('Migration: ' + phase, flush=True)
    switched = False
    record('preflight-verified')
    try:
        guest(112, 'docker', 'stop', '--time', '60', SOURCE[0], SOURCE[1])
        source_counts = counts(112, 'blog-umami-db')
        (rollback / 'postgres-counts.txt').write_text(source_counts)
        with (rollback / 'umami.dump').open('wb') as stream:
            guest(112, 'docker', 'exec', 'blog-umami-db', 'pg_dump', '-U', 'umami', '-d', 'umami', '-Fc', stdout=stream)
        guest(112, 'docker', 'stop', '--time', '60', 'blog-umami-db')
        grafana_counts = checked_sqlite(OLD / 'grafana/grafana.db')
        run('cp', '-a', str(OLD / 'grafana') + '/.', str(NEW / 'grafana'))
        if checked_sqlite(NEW / 'grafana/grafana.db') != grafana_counts:
            raise RuntimeError('Grafana restore count mismatch')
        (rollback / 'grafana-counts.json').write_text(json.dumps(grafana_counts) + '\n')
        compose('observability', 'up', '-d', '--pull', 'never', '--wait', '--wait-timeout', '120', 'postgres')
        if counts(110, 'umami-db').strip():
            raise RuntimeError('Target PostgreSQL schema must be empty')
        with (rollback / 'umami.dump').open('rb') as stream:
            guest(110, 'docker', 'exec', '-i', 'umami-db', 'pg_restore', '-U', 'umami', '-d', 'umami',
                  '--exit-on-error', '--no-owner', '--no-privileges', stdin=stream,
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if counts(110, 'umami-db') != source_counts:
            raise RuntimeError('Restored Umami table counts differ')
        record('database-restore-and-grafana-integrity-verified')
        for ctid, prefix in ((114, 'blog'), (115, 'production')):
            guest(ctid, 'docker', 'stop', prefix + '-observability-alloy-1')
        guest(112, 'docker', 'stop', '--time', '60', 'prometheus', 'loki')
        for name in ('prometheus', 'loki'):
            run('cp', '-a', str(APPDATA / name), str(rollback / name))
            # Compare every file byte-for-byte while both stores are stopped.
            run('diff', '-qr', str(APPDATA / name), str(rollback / name), stdout=subprocess.DEVNULL)
        with (rollback / 'SHA256SUMS').open('w') as stream:
            run('sha256sum', 'umami.dump', cwd=rollback, stdout=stream)
        record('stopped-store-rollback-copies-verified')
        # Preserve activation state; update the existing production targets only.
        active = bool(json.loads((APPDATA / 'production-monitoring/https.json').read_text()))
        if active:
            guest(110, 'python3', release + '/hosts/production/observability/configure.py', '--activate-targets')
        compose('loki', 'up', '-d', '--pull', 'never')
        compose('prometheus', 'up', '-d', '--pull', 'never', '--wait', '--wait-timeout', '120')
        guest(110, 'bash', shared + '/deploy.sh')
        # Prometheus/Loki are now the sole writers; keep source containers stopped on reboot.
        guest(112, 'docker', 'update', '--restart=no', *SOURCE)
        for ctid, prefix, folder, envkey in ((114, 'blog', 'staging/blog-observability', 'BLOG_OBSERVABILITY_COMMIT'),
                                           (115, 'production', 'production/observability', 'PRODUCTION_PLATFORM_COMMIT')):
            guest(ctid, 'docker', 'stop', prefix + '-observability-blackbox-1')
            guest(ctid, 'docker', 'update', '--restart=no', prefix + '-observability-blackbox-1')
            config = release + '/hosts/' + folder + '/compose.yaml'
            args = ('env', envkey + '=' + commit, 'docker', 'compose', '--env-file', '/dev/null', '-f', config)
            guest(ctid, *args, 'config', '--quiet')
            guest(ctid, *args, 'up', '-d', '--pull', 'never', 'alloy')
        guest(110, 'curl', '-fsS', '-o', '/dev/null', 'http://192.168.0.110:3100/ready')
        # From this point analytics writes may reach the new database.
        switched = True
        record('switching-routes')
        guest(110, 'python3', shared + '/configure-routes.py')
        for ctid in EXPECTED:
            promote(ctid, release, commit)
            if ctid in (110, 114, 115):
                guest(ctid, 'install', '-d', '/opt/dothomelab-production')
                guest(ctid, 'ln', '-sfn', release, '/opt/dothomelab-production/current')
        guest(110, 'ln', '-sfn', release, '/opt/dothomelab-observability/current')
        run('bash', release + '/hosts/infra/observability/install-fleet.sh')
        run('install', '-m', '0755', str(repo / 'backup/pbs/blog-umami-database-backup.sh'),
            '/etc/dothomelab/backup-pre.d/70-blog-umami-database')
        run('bash', '/etc/dothomelab/backup-pre.d/70-blog-umami-database')
        record('complete')
    except BaseException:
        if not switched:
            for folder in ('observability', 'prometheus', 'loki'):
                compose(folder, 'stop')
            guest(112, 'docker', 'update', '--restart=unless-stopped', *SOURCE)
            guest(112, 'docker', 'start', 'blog-umami-db', *SOURCE[:2], 'prometheus', 'loki')
            for ctid, prefix in ((114, 'blog'), (115, 'production')):
                folder = 'staging/blog-observability' if ctid == 114 else 'production/observability'
                guest(ctid, 'docker', 'update', '--restart=unless-stopped', prefix + '-observability-blackbox-1')
                args = ('docker', 'compose', '--env-file', '/dev/null', '-f', '/opt/dothomelab/hosts/' + folder + '/compose.yaml')
                guest(ctid, *args, 'config', '--quiet')
                guest(ctid, *args, 'up', '-d', '--pull', 'never')
            record('failed-before-cutover-source-restarted')
        raise
    print('Migration complete; retained rollback: ' + str(rollback))


if __name__ == '__main__':
    os.umask(0o077)
    try:
        main()
    except Exception as error:
        raise SystemExit(f'Migration stopped ({type(error).__name__}: {error}); inspect retained phase before retrying') from None
