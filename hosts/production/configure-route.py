#!/usr/bin/env python3
"""CT110: inspect or explicitly publish the existing rafael.ink apex route."""
import argparse
import fcntl
import json
from pathlib import Path
import sqlite3
import subprocess
import time

DATA = Path('/srv/appdata/docker/infra-nginx-proxy-manager')
DB = DATA / 'data/database.sqlite'
HERE = Path(__file__).resolve().parent


def check(database):
    rows = database.execute('SELECT id,domain_names,forward_host,forward_port,certificate_id,advanced_config FROM proxy_host WHERE is_deleted=0').fetchall()
    matching = [row for row in rows if 'rafael.ink' in json.loads(row[1])]
    if len(matching) != 1 or json.loads(matching[0][1]) != ['rafael.ink']:
        raise RuntimeError('Apex route absent, duplicated or shared; inspect before publication')
    row = matching[0]
    if (row[2], row[3]) not in (('localhost', 8888), ('192.168.0.115', 8084)):
        raise RuntimeError('Apex route has an unexpected owner/upstream; refusing replacement')
    domains = database.execute('SELECT domain_names FROM certificate WHERE id=? AND is_deleted=0', (row[4],)).fetchone()
    if not domains or 'rafael.ink' not in json.loads(domains[0]):
        raise RuntimeError('Certificate does not cover apex rafael.ink')
    return row


def render(row_id):
    code = (HERE / 'render-route.mjs').read_text().replace('ROUTE_ID', str(row_id))
    result = subprocess.run(['docker', 'exec', '-i', 'nginx-proxy-manager', 'node', '--input-type=module'],
                            input=code, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('NPM route rendering failed; inspect privately')
    subprocess.run(['docker', 'exec', 'nginx-proxy-manager', 'nginx', '-t'], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-rafael-ink', action='store_true')
    args = parser.parse_args()
    with open('/run/lock/dothomelab-npm-routes.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with sqlite3.connect(DB) as database:
            row = check(database)
            if not args.publish_rafael_ink:
                print(f'Apex route {row[0]} and apex certificate verified; upstream {row[2]}:{row[3]} unchanged')
                return
            database.row_factory = sqlite3.Row
            original = dict(database.execute('SELECT * FROM proxy_host WHERE id=?', (row[0],)).fetchone())
            backup = DATA / f'production-route-before-{time.time_ns()}'
            backup.mkdir(mode=0o700)
            with sqlite3.connect(backup / 'database.sqlite') as target:
                database.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('NPM rollback backup failed integrity check')
            (backup / 'route.json').write_text(json.dumps(original, indent=2) + '\n')
            (backup / 'route.json').chmod(0o600)
            (backup / 'database.sqlite').chmod(0o600)
            config = (HERE / 'telemetry.nginx.conf').read_text()
            database.execute('UPDATE proxy_host SET forward_scheme=?,forward_host=?,forward_port=?,enabled=1,ssl_forced=1,access_list_id=0,advanced_config=?,modified_on=datetime(\'now\') WHERE id=?',
                             ('http', '192.168.0.115', 8084, config, row[0]))
            database.commit()
            try:
                render(row[0])
            except Exception:
                fields = ('forward_scheme','forward_host','forward_port','enabled','ssl_forced','access_list_id','advanced_config')
                database.execute('UPDATE proxy_host SET ' + ','.join(key + '=?' for key in fields) + ' WHERE id=?',
                                 (*[original[key] for key in fields], row[0]))
                database.commit()
                render(row[0])
                raise
            print('Published https://rafael.ink; focused route rollback retained at ' + str(backup))


if __name__ == '__main__':
    main()
