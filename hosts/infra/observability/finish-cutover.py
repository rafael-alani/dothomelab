#!/usr/bin/env python3
"""PVE: finish a recorded cutover without repeating any data migration."""
import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess

HERE = Path(__file__).resolve().parent
migration = runpy.run_path(str(HERE / 'migrate-to-infra.py'))
run, guest, output = (migration[k] for k in ('run', 'guest', 'output'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rollback', type=Path)
    args = parser.parse_args()
    rollback = args.rollback.resolve()
    if os.geteuid() != 0 or rollback.parent != migration['NEW'] or not rollback.name.startswith('rollback-'):
        raise RuntimeError('Use the recorded rollback directory on PVE')
    state = json.loads((rollback / 'migration.json').read_text())
    if state['phase'] != 'switching-routes':
        raise RuntimeError('Only an interrupted routing cutover can be finished here')
    repo = Path(output('git', 'rev-parse', '--show-toplevel'))
    commit = output('git', 'rev-parse', 'HEAD')
    if output('git', 'status', '--porcelain'):
        raise RuntimeError('Use a clean committed checkout')
    for name in migration['SOURCE']:
        if output('pct', 'exec', '112', '--', 'docker', 'inspect', '--format', '{{.State.Running}}', name) != 'false':
            raise RuntimeError('Source must remain stopped; never introduce competing writers')
    for name in ('umami-db', 'umami', 'grafana', 'prometheus', 'loki', 'blackbox', 'observability-fleet'):
        if output('pct', 'exec', '110', '--', 'docker', 'inspect', '--format', '{{.State.Running}}', name) != 'true':
            raise RuntimeError('Target must already be running: ' + name)
    for ctid, expected in migration['EXPECTED'].items():
        current = output('pct', 'exec', str(ctid), '--', 'cat', '/opt/dothomelab/DEPLOYED_COMMIT')
        if current not in (expected, commit):
            raise RuntimeError(f'CT{ctid} source drift; reconcile before finishing')
    run('bash', str(HERE / 'install-source.sh'), '--archive-only')
    release = '/opt/dothomelab-observability/releases/' + commit
    archive = Path('/run/observability-finish-' + commit + '.tar')
    with archive.open('wb') as stream: run('git', 'archive', 'HEAD', stdout=stream)
    for ctid in migration['EXPECTED']:
        guest(ctid, 'install', '-d', '-m', '0755', release)
        run('pct', 'push', str(ctid), str(archive), '/run/observability-finish.tar', '--perms', '0600')
        guest(ctid, 'tar', '-xf', '/run/observability-finish.tar', '-C', release)
        guest(ctid, 'sh', '-c', 'printf "%s\n" "$1" >"$2/DEPLOYED_COMMIT"', 'sh', commit, release)
        guest(ctid, 'rm', '/run/observability-finish.tar')
    archive.unlink()
    guest(110, 'python3', release + '/hosts/infra/observability/configure-routes.py')
    for ctid in migration['EXPECTED']:
        current = output('pct', 'exec', str(ctid), '--', 'cat', '/opt/dothomelab/DEPLOYED_COMMIT')
        if current != commit: migration['promote'](ctid, release, commit)
        if ctid in (110, 114, 115):
            guest(ctid, 'install', '-d', '/opt/dothomelab-production')
            guest(ctid, 'ln', '-sfn', release, '/opt/dothomelab-production/current')
    guest(110, 'ln', '-sfn', release, '/opt/dothomelab-observability/current')
    run('bash', release + '/hosts/infra/observability/install-fleet.sh')
    run('install', '-m', '0755', str(repo / 'backup/pbs/blog-umami-database-backup.sh'),
        '/etc/dothomelab/backup-pre.d/70-blog-umami-database')
    run('bash', '/etc/dothomelab/backup-pre.d/70-blog-umami-database')
    state.update(phase='complete', completion_source_commit=commit)
    (rollback / 'migration.json').write_text(json.dumps(state, indent=2) + '\n')
    print('Cutover completed; original data and rollback retained. End-to-end acceptance follows.')


if __name__ == '__main__':
    os.umask(0o077)
    main()
