#!/usr/bin/env python3
"""PVE-owned, credential-free discovery for the dedicated Homarr Staging board."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

# This script is also executed from stdin in CT110: defer staging imports to discovery.
SUFFIX = '.staging.rafael.media'
HOST = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.staging\.rafael\.media')
REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
APPDATA = Path('/srv/appdata/docker')
HOMARR = APPDATA / 'homarr'
MANIFEST = 'staging-board-managed.json'
SOURCE = Path(__file__).resolve()


def identifier(kind, key):
    return 'dhlstg' + kind + hashlib.sha256(key.encode()).hexdigest()[:16]


def encoded(value):
    return json.dumps({'json': value}, separators=(',', ':'))


def read_json(path):
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Inventory file exceeds limit')
    return json.loads(path.read_text())


def validate(apps):
    if not isinstance(apps, list) or len(apps) > 200:
        raise ValueError('Invalid application inventory')
    keys, hosts = set(), set()
    for app in apps:
        if set(app) != {'key', 'name', 'hostname', 'description', 'kind'}:
            raise ValueError('Unexpected application fields')
        if (not isinstance(app['key'], str) or len(app['key']) > 250
                or not HOST.fullmatch(app['hostname']) or app['kind'] not in {'compose', 'symphony'}):
            raise ValueError('Invalid staging identity')
        if app['key'] in keys or app['hostname'] in hosts:
            raise ValueError('Duplicate staging identity')
        for field in ['name', 'description']:
            value = app[field]
            if not isinstance(value, str) or not value or len(value) > 300 or any(ord(c) < 32 for c in value):
                raise ValueError('Invalid display text')
        keys.add(app['key'])
        hosts.add(app['hostname'])
    return sorted(apps, key=lambda a: (a['kind'], a['name'], a['key']))


def discover(registry, staging):
    """Read declared Compose apps and enabled Symphony routes, never archives."""
    if not isinstance(registry, dict):
        raise ValueError('Invalid Compose registry')
    from lifecycle import retired
    apps = []
    for name, app in registry.items():
        if retired(app["repository"], staging / "retired"):
            continue
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', name):
            raise ValueError('Invalid Compose name')
        current = staging / name / 'current.json'
        kind = 'Static' if app.get('runtime') == 'static' else 'Compose'
        description = kind + ' staging application; awaiting first deployment.'
        if current.exists():
            state = read_json(current)
            if not re.fullmatch(r'[a-f0-9]{40}', state['commit']):
                raise ValueError('Invalid accepted Compose commit')
            description = kind + ' staging application; accepted commit ' + state['commit'][:12] + '.'
        apps.append(dict(key='compose:' + name, name=name.replace('-', ' ').title(),
                         hostname=app['hostname'], description=description, kind='compose'))
    symphony = staging / 'symphony'
    if symphony.exists():
        routes = read_json(symphony / 'control/routes.json')
        if not isinstance(routes, dict):
            raise ValueError('Invalid Symphony routes')
        for repository, route in routes.items():
            if not REPO.fullmatch(repository) or type(route.get('enabled', True)) is not bool:
                raise ValueError('Invalid Symphony registration')
            if not route.get('enabled', True) or retired(repository, staging / 'retired'):
                continue
            hostname = route['hostname']
            if not HOST.fullmatch(hostname):
                raise ValueError('Invalid Symphony hostname')
            apps.append(dict(key='symphony:' + repository,
                             name=hostname[:-len(SUFFIX)].replace('-', ' ').title(),
                             hostname=hostname, kind='symphony',
                             description='Symphony staging application: ' + repository))
    return validate(apps)


def home_settings(db):
    return [db.execute(q).fetchall() for q in (
        'SELECT id,home_board_id,mobile_home_board_id FROM user ORDER BY id',
        'SELECT id,home_board_id,mobile_home_board_id FROM "group" ORDER BY id',
        "SELECT value FROM serverSetting WHERE setting_key='board'",
    )]


def check_board(db, board):
    row = db.execute('SELECT name,is_public FROM board WHERE id=?', (board,)).fetchone()
    if row != ('Staging', 0):
        raise ValueError('Managed board must remain private and named Staging')
    for table in ['user', 'group']:
        if db.execute('SELECT 1 FROM "' + table + '" WHERE home_board_id=? OR mobile_home_board_id=?',
                      (board, board)).fetchone():
            raise ValueError('Refusing to manage a home board')
    setting = db.execute("SELECT value FROM serverSetting WHERE setting_key='board'").fetchone()
    if setting:
        values = json.loads(setting[0])['json']
        if board in (values.get('homeBoardId'), values.get('mobileHomeBoardId')):
            raise ValueError('Refusing to manage the server home board')
    for kind, options in db.execute('SELECT kind,options FROM item WHERE board_id=?', (board,)):
        if kind != 'app':
            raise ValueError('Managed board contains an unsupported widget')
        app = db.execute('SELECT href FROM app WHERE id=?', (json.loads(options)['json']['appId'],)).fetchone()
        if not app or not re.fullmatch('https://' + HOST.pattern, app[0]):
            raise ValueError('Managed board contains a non-staging app')


def rows_for(board, apps):
    root, section = identifier('r', board), identifier('s', board)
    rows = {
        'app': [], 'item': [], 'layout': [], 'item_layout': [],
        'section': [dict(id=root, board_id=board, kind='empty', x_offset=0, y_offset=0, options=encoded({})),
                    dict(id=section, board_id=board, kind='container', x_offset=None, y_offset=None,
                         options=encoded(dict(title='Staging apps', customCssClasses=[], borderColor='#7950f2',
                                              showLabel=True, collapsible=False, showOpenAll=False, scrollable=False)))],
        'section_layout': [],
    }
    for name, columns, breakpoint, role in [('Desktop', 8, 1080, 'base'), ('Compact', 6, 720, 'custom'), ('Mobile', 4, 0, 'mobile')]:
        layout = identifier('l', board + name)
        rows['layout'].append(dict(id=layout, name=name, board_id=board, column_count=columns, breakpoint=breakpoint, role=role))
        rows['section_layout'].append(dict(section_id=section, layout_id=layout, parent_section_id=root,
                                           x_offset=0, y_offset=0, width=columns,
                                           height=max(3, ((len(apps) + columns // 2 - 1) // (columns // 2)) * 2 + 1)))
        for index, app in enumerate(apps):
            rows['item_layout'].append(dict(item_id=identifier('i', app['key']), section_id=section, layout_id=layout,
                                            x_offset=(index % (columns // 2)) * 2, y_offset=(index // (columns // 2)) * 2,
                                            width=2, height=2))
    for app in apps:
        aid = identifier('a', app['key'])
        icon = 'docker' if app['kind'] == 'compose' else 'github'
        rows['app'].append(dict(id=aid, name=app['name'], description=app['description'],
                               icon_url='https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/' + icon + '.svg',
                               href='https://' + app['hostname'], ping_url=None))
        rows['item'].append(dict(id=identifier('i', app['key']), board_id=board, kind='app',
                                options=encoded(dict(appId=aid, openIn='newTab', pingEnabled=False, showTitle=True,
                                                     layout='column', descriptionDisplayMode='tooltip')),
                                advanced_options=encoded({})))
    return rows


def matches(db, board, desired):
    for table, rows in desired.items():
        if not rows:
            if table in {'item', 'app', 'item_layout'}:
                if db.execute('SELECT 1 FROM item WHERE board_id=?', (board,)).fetchone():
                    return False
            continue
        columns = list(rows[0])
        wanted = sorted([tuple(row[k] for k in columns) for row in rows], key=repr)
        if table == 'app':
            query = 'SELECT ' + ','.join(columns) + ' FROM app WHERE id IN (' + ','.join('?' for _ in rows) + ')'
            params = [row['id'] for row in rows]
        elif table in {'item_layout', 'section_layout'}:
            query = 'SELECT ' + ','.join(columns) + ' FROM ' + table + ' WHERE layout_id IN (SELECT id FROM layout WHERE board_id=?)'
            params = [board]
        else:
            query = 'SELECT ' + ','.join(columns) + ' FROM ' + table + ' WHERE board_id=?'
            params = [board]
        if sorted(db.execute(query, params).fetchall(), key=repr) != wanted:
            return False
    return True


def reconcile(apps, directory=HOMARR, adopt=None, check=False):
    apps = validate(apps)
    manifest = directory / MANIFEST
    board = read_json(manifest)['board_id'] if manifest.exists() else adopt
    db = sqlite3.connect('file:' + str(directory / 'db/db.sqlite') + '?mode=rw', uri=True, timeout=30)
    db.execute('PRAGMA foreign_keys=ON')
    try:
        db.execute('BEGIN IMMEDIATE')
        before = home_settings(db)
        if board:
            check_board(db, board)
        else:
            if db.execute("SELECT 1 FROM board WHERE lower(name)='staging'").fetchone():
                raise ValueError('Existing Staging board requires explicit --adopt-board ID')
            board = identifier('b', 'Staging')
            if check:
                return dict(changed=True, apps=len(apps))
            owner = db.execute('SELECT user_id FROM groupMember JOIN "group" ON "group".id=groupMember.group_id '
                               'WHERE "group".name=? ORDER BY user_id LIMIT 1', ('credentials-admin',)).fetchone()
            if not owner:
                raise ValueError('Homarr admin account must be initialized first')
            db.execute('INSERT INTO board(id,name,is_public,creator_id,page_title,meta_title,primary_color,secondary_color) '
                       'VALUES(?,?,?,?,?,?,?,?)', (board, 'Staging', 0, owner[0], 'Staging', 'Staging · Homarr', '#7950f2', '#15aabf'))
        desired = rows_for(board, apps)
        changed = not matches(db, board, desired)
        if check:
            return dict(changed=changed, apps=len(apps))
        if changed:
            old_apps = [json.loads(row[0])['json']['appId'] for row in db.execute('SELECT options FROM item WHERE board_id=?', (board,))]
            # Refuse sharing of managed app records: changes must stay on this board.
            for app in desired['app']:
                if db.execute("SELECT 1 FROM item WHERE board_id!=? AND json_extract(options,'$.json.appId')=?", (board, app['id'])).fetchone():
                    raise ValueError('Managed app is referenced by another board')
            db.execute('DELETE FROM item WHERE board_id=?', (board,))
            db.execute('DELETE FROM layout WHERE board_id=?', (board,))
            db.execute('DELETE FROM section WHERE board_id=?', (board,))
            for table in ['app', 'section', 'layout', 'section_layout', 'item', 'item_layout']:
                for row in desired[table]:
                    columns = list(row)
                    updates = ','.join(k + '=excluded.' + k for k in columns if k != 'id')
                    sql = 'INSERT INTO ' + table + '(' + ','.join(columns) + ') VALUES(' + ','.join('?' for _ in columns) + ')'
                    if table == 'app':
                        sql += ' ON CONFLICT(id) DO UPDATE SET ' + updates
                    db.execute(sql, list(row.values()))
            for aid in old_apps:
                if not db.execute("SELECT 1 FROM item WHERE json_extract(options,'$.json.appId')=?", (aid,)).fetchone() \
                        and not db.execute('SELECT 1 FROM integration WHERE app_id=?', (aid,)).fetchone():
                    db.execute('DELETE FROM app WHERE id=?', (aid,))
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Homarr integrity check failed')
            assert matches(db, board, desired)
        assert before == home_settings(db), 'Home defaults changed'
        # Write only once. Ownership is explicit; DB writes remain one transaction.
        if not manifest.exists():
            pending = manifest.with_suffix('.pending')
            pending.write_text(json.dumps(dict(board_id=board, version=1)) + '\n')
            pending.chmod(0o600)
            os.replace(pending, manifest)
        db.commit()
        return dict(changed=changed, apps=len(apps))
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', help=argparse.SUPPRESS)
    parser.add_argument('--adopt-board')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    with open('/run/lock/dothomelab-staging-homarr.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.apply is not None:
            result = reconcile(json.loads(args.apply), adopt=args.adopt_board, check=args.check)
        else:
            if not Path('/etc/pve').is_dir():
                raise ValueError('Run on PVE')
            output = subprocess.run(['pct', 'exec', '114', '--', 'cat', '/opt/dothomelab/hosts/staging/apps.json'],
                                    capture_output=True, text=True, check=True, timeout=30).stdout
            apps = discover(json.loads(output), APPDATA / 'staging')
            command = ['pct', 'exec', '110', '--', 'python3', '-', '--apply', json.dumps(apps)]
            if args.adopt_board:
                command += ['--adopt-board', args.adopt_board]
            if args.check:
                command += ['--check']
            process = subprocess.run(command, input=SOURCE.read_text(), capture_output=True,
                                     text=True, timeout=60)
            if process.returncode not in ({0, 1} if args.check else {0}):
                raise RuntimeError('Infra reconciliation failed')
            result = json.loads(process.stdout)
        print(json.dumps(result))
        return int(args.check and result['changed'])


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Inventory and subprocess output can contain application-controlled text.
        print('Staging Homarr sync failed: ' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1) from None
