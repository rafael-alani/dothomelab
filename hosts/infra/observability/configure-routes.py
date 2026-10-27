#!/usr/bin/env python3
"""CT110: reconcile private shared routes and existing blog collection endpoints."""
import fcntl
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import tomllib

HERE = Path(__file__).resolve().parent
DATA = Path('/srv/appdata/docker/infra-nginx-proxy-manager')
ROUTES = {'analytics.rafael.media': 8090, 'grafana.rafael.media': 8091,
          'prometheus.rafael.media': 9092, 'loki.rafael.media': 3100,
          'analytics.staging.rafael.media': 8090, 'grafana.staging.rafael.media': 8091}
PRIVATE = 'allow 192.168.0.0/24;\nallow 100.64.0.0/10;\ndeny all;\nproxy_buffering off;\nproxy_read_timeout 3600s;'


def render(row_id):
    code = (HERE.parents[1] / 'production/render-route.mjs').read_text().replace('ROUTE_ID', str(row_id))
    result = subprocess.run(['docker', 'exec', '-i', 'nginx-proxy-manager', 'node', '--input-type=module'],
                            input=code, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('NPM rendering failed; inspect privately')


def main():
    with open('/run/lock/dothomelab-npm-routes.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        backup = DATA / ('observability-route-before-' + str(time.time_ns()))
        backup.mkdir(mode=0o700)
        with sqlite3.connect(DATA / 'data/database.sqlite') as db:
            db.row_factory = sqlite3.Row
            with sqlite3.connect(backup / 'database.sqlite') as target:
                db.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Proxy rollback integrity failed')
            (backup / 'database.sqlite').chmod(0o600)
            rows = db.execute('SELECT * FROM proxy_host WHERE is_deleted=0').fetchall()
            certificates = db.execute('SELECT id,domain_names FROM certificate WHERE is_deleted=0').fetchall()
            original, changed, created = {}, [], []
            committed = False
            try:
                for domain, port in ROUTES.items():
                    matches = [row for row in rows if domain in json.loads(row['domain_names'])]
                    if len(matches) > 1 or (matches and (json.loads(matches[0]['domain_names']) != [domain]
                            or matches[0]['forward_host'] not in ('192.168.0.110','192.168.0.112','192.168.0.114'))):
                        raise RuntimeError('Shared route ownership conflict')
                    wildcard = '*.staging.rafael.media' if '.staging.' in domain else '*.rafael.media'
                    cert = next(row['id'] for row in certificates if wildcard in json.loads(row['domain_names']))
                    values = dict(owner_user_id=rows[0]['owner_user_id'], domain_names=json.dumps([domain]),
                        forward_scheme='http',forward_host='192.168.0.110',forward_port=port,
                        access_list_id=0,certificate_id=cert,ssl_forced=1,caching_enabled=0,
                        block_exploits=1,allow_websocket_upgrade=1,http2_support=1,enabled=1,is_deleted=0,
                        locations='[]',meta='{}',hsts_enabled=0,hsts_subdomains=0,advanced_config=PRIVATE)
                    if matches:
                        row = matches[0]; original[row['id']] = dict(row)
                        db.execute('UPDATE proxy_host SET '+','.join(k+'=?' for k in values)+",modified_on=datetime('now') WHERE id=?",(*values.values(),row['id']))
                        changed.append(row['id'])
                    else:
                        cursor=db.execute('INSERT INTO proxy_host ('+','.join(values)+',created_on,modified_on) VALUES ('+','.join('?' for _ in values)+",datetime('now'),datetime('now'))",tuple(values.values()))
                        created.append(cursor.lastrowid); changed.append(cursor.lastrowid)
                telemetry = (HERE.parents[1] / 'production/telemetry.nginx.conf').read_text()
                for domain in ('rafael.ink','blog.staging.rafael.media'):
                    matches=[r for r in rows if json.loads(r['domain_names']) == [domain]]
                    if not matches:
                        continue  # Clean bootstrap has not published this application yet.
                    row=matches[0]
                    expected='192.168.0.115' if domain=='rafael.ink' else '192.168.0.114'
                    if row['forward_host'] != expected:
                        continue  # Never activate a dormant public site during monitoring setup.
                    old=row['advanced_config'] or ''
                    if domain=='rafael.ink':
                        if 'location = /telemetry/script.js' not in old:
                            raise RuntimeError('Published blog telemetry configuration is unexpected')
                        config=old.replace('http://192.168.0.112:8090/','http://192.168.0.110:8090/')
                    else:
                        config=PRIVATE+'\n'+telemetry
                    original[row['id']]=dict(row)
                    db.execute('UPDATE proxy_host SET advanced_config=? WHERE id=?',(config,row['id']))
                    changed.append(row['id'])
                (backup / 'routes.json').write_text(json.dumps({'original':original,'created':created},indent=2)+'\n')
                (backup / 'routes.json').chmod(0o600)
                db.commit()
                committed = True
                for row_id in changed: render(row_id)
                subprocess.run(['docker','exec','nginx-proxy-manager','nginx','-t'],check=True,capture_output=True)
            except Exception:
                db.rollback()
                for row_id,row in original.items():
                    fields={k:v for k,v in row.items() if k!='id'}
                    db.execute('UPDATE proxy_host SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',(*fields.values(),row_id))
                for row_id in created:
                    db.execute('UPDATE proxy_host SET enabled=0 WHERE id=?',(row_id,))
                db.commit()
                for row_id in (changed if committed else original): render(row_id)
                raise
    config=Path('/srv/appdata/docker/pihole/etc-pihole/pihole.toml')
    current=tomllib.loads(config.read_text())['dns']['hosts']
    desired=[line for line in current if not (len(parts:=line.split())==2 and parts[1] in ROUTES)]
    desired += ['192.168.0.110 '+name for name in sorted(ROUTES)]
    if desired != current:
        subprocess.run(['docker','exec','pihole','pihole-FTL','--config','dns.hosts',json.dumps(desired)],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['docker','exec','pihole','pihole','reloaddns'],check=True,stdout=subprocess.DEVNULL)
    homarr = Path('/srv/appdata/docker/homarr/db/db.sqlite')
    if homarr.is_file():
        with sqlite3.connect(homarr) as db, sqlite3.connect(backup / 'homarr.sqlite') as snapshot:
            db.backup(snapshot)
            if snapshot.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Homarr backup integrity failed')
            for app_id, old, new in (
                ('dhlprometheusapp000001', 'http://192.168.0.112:9090/-/ready', 'http://192.168.0.110:9092/-/ready'),
                ('dhllokiapp000000000001', 'http://192.168.0.112:3100/ready', 'http://192.168.0.110:3100/ready')):
                db.execute('UPDATE app SET ping_url=? WHERE id=? AND ping_url=?', (new, app_id, old))
            db.commit()
        (backup / 'homarr.sqlite').chmod(0o600)
    print('Private shared routes and existing blog collection updated; rollback: '+str(backup))


if __name__ == '__main__':
    main()
