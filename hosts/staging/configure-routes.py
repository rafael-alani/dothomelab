#!/usr/bin/env python3
"""Add only declared staging routes inside Infra; keep LAN/Tailscale ACLs."""
import argparse
import fcntl
import json
import sqlite3
import subprocess
from pathlib import Path

from lifecycle import retired_hostname

HERE = Path(__file__).resolve().parent
APPDATA = Path('/srv/appdata/docker/infra-nginx-proxy-manager')


SHARED_OBSERVABILITY_HOSTNAMES = {'analytics.staging.rafael.media', 'grafana.staging.rafael.media'}


def route_upstream(app: dict) -> str:
    host = app.get('forward_host', '192.168.0.114')
    if host != '192.168.0.114' and not (
        host == '192.168.0.112' and app['hostname'] in SHARED_OBSERVABILITY_HOSTNAMES
    ):
        raise RuntimeError('Only the two shared observability routes may use Apps')
    return host


def check_existing_route(app: dict, rows: list) -> str:
    host = route_upstream(app)
    allowed = {host}
    if host == '192.168.0.112':
        allowed.add('192.168.0.114')
    if len(rows) > 1 or (rows and rows[0][1] not in allowed):
        raise RuntimeError('Staging route conflicts with an existing route')
    return host


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apps', type=Path, default=HERE / 'apps.json')
    args = parser.parse_args()
    apps = {name: app for name, app in json.loads(args.apps.read_text()).items()
            if not retired_hostname(app['hostname'])}
    for app in apps.values():
        route_upstream(app)
    if not apps:
        print('No active staging routes to configure')
        return
    with open('/run/lock/dothomelab-npm-routes.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        apps = {name: app for name, app in apps.items() if not retired_hostname(app['hostname'])}
        if not apps:
            return
        with sqlite3.connect(APPDATA / 'data/database.sqlite') as database:
            if database.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise RuntimeError('NPM database integrity failed')
            backup = APPDATA / 'database.sqlite.pre-staging'
            if not backup.exists():
                with sqlite3.connect(backup) as target:
                    database.backup(target)
                    if target.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                        raise RuntimeError('NPM rollback integrity failed')
                backup.chmod(0o600)
        # Issue once using NPM's existing DNS-01 account. No public app record or
        # router change is necessary. NPM owns renewal and canonical certificate data.
        result = subprocess.run(['docker', 'exec', '-i', 'nginx-proxy-manager', 'node', '--input-type=module'],
                                input=(HERE / 'ensure-certificate.mjs').read_text(), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise RuntimeError('Staging wildcard issuance failed; inspect NPM privately')
        with sqlite3.connect(APPDATA / 'data/database.sqlite') as database:
            certificates = database.execute('SELECT id,domain_names FROM certificate WHERE is_deleted=0').fetchall()
            cert = next(cid for cid, domains in certificates if '*.staging.rafael.media' in json.loads(domains))
            owner = database.execute('SELECT owner_user_id FROM proxy_host WHERE is_deleted=0 ORDER BY id LIMIT 1').fetchone()[0]
            for app in apps.values():
                domain = json.dumps([app['hostname']], separators=(',', ':'))
                rows = database.execute('SELECT id,forward_host FROM proxy_host WHERE domain_names=? AND is_deleted=0', (domain,)).fetchall()
                upstream = check_existing_route(app, rows)
                values = {
                    'owner_user_id': owner, 'domain_names': domain, 'forward_scheme': 'http',
                    'forward_host': upstream, 'forward_port': app['port'],
                    'access_list_id': 0, 'certificate_id': cert, 'ssl_forced': 1,
                    'caching_enabled': 0, 'block_exploits': 1, 'allow_websocket_upgrade': 1,
                    'http2_support': 1, 'enabled': 1, 'is_deleted': 0, 'locations': '[]',
                    'meta': '{}', 'hsts_enabled': 0, 'hsts_subdomains': 0,
                    'advanced_config': 'allow 192.168.0.0/24;\nallow 100.64.0.0/10;\ndeny all;\nproxy_buffering off;\nproxy_read_timeout 3600s;',
                }
                if rows:
                    database.execute('UPDATE proxy_host SET ' + ','.join(f'{key}=?' for key in values)
                                     + ",modified_on=datetime('now') WHERE id=?", (*values.values(), rows[0][0]))
                else:
                    database.execute('INSERT INTO proxy_host (' + ','.join(values) + ',created_on,modified_on) VALUES ('
                                     + ','.join('?' for _ in values) + ",datetime('now'),datetime('now'))", tuple(values.values()))
        subprocess.run(['docker', 'exec', '-i', 'nginx-proxy-manager', 'node', '--input-type=module'],
                       input=(HERE / 'reconcile-routes.mjs').read_text(), text=True, check=True)
        subprocess.run(['docker', 'exec', 'nginx-proxy-manager', 'nginx', '-t'], check=True)
    # Additive Pi-hole edits preserve every non-staging record.
    import tomllib
    with open('/srv/appdata/docker/pihole/etc-pihole/pihole.toml', 'rb') as handle:
        current = tomllib.load(handle)['dns']['hosts']
    domains = {app['hostname'] for app in apps.values()}
    desired = [line for line in current if not (len(parts := line.split()) == 2 and parts[1] in domains)]
    desired += [f'192.168.0.110 {domain}' for domain in sorted(domains)]
    if desired != current:
        subprocess.run(['docker', 'exec', 'pihole', 'pihole-FTL', '--config', 'dns.hosts', json.dumps(desired)],
                       stdout=subprocess.DEVNULL, check=True)
        subprocess.run(['docker', 'exec', 'pihole', 'pihole', 'reloaddns'], stdout=subprocess.DEVNULL, check=True)
    print('Private staging TLS routes and exact local DNS records reconciled')


if __name__ == '__main__':
    main()
