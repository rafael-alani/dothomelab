#!/usr/bin/env python3
"""Disposable SQLite tests for staging discovery and board isolation."""
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('sync_homarr', Path(__file__).with_name('sync-homarr.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

SCHEMA = '''
CREATE TABLE user(id TEXT PRIMARY KEY,home_board_id TEXT,mobile_home_board_id TEXT);
CREATE TABLE "group"(id TEXT PRIMARY KEY,name TEXT,home_board_id TEXT,mobile_home_board_id TEXT);
CREATE TABLE groupMember(group_id TEXT,user_id TEXT);
CREATE TABLE serverSetting(setting_key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE board(id TEXT PRIMARY KEY,name TEXT,is_public INTEGER,creator_id TEXT,page_title TEXT,
meta_title TEXT,primary_color TEXT,secondary_color TEXT);
CREATE TABLE app(id TEXT PRIMARY KEY,name TEXT,description TEXT,icon_url TEXT,href TEXT,ping_url TEXT);
CREATE TABLE integration(id TEXT PRIMARY KEY,app_id TEXT REFERENCES app(id));
CREATE TABLE item(id TEXT PRIMARY KEY,board_id TEXT REFERENCES board(id),kind TEXT,options TEXT,advanced_options TEXT);
CREATE TABLE section(id TEXT PRIMARY KEY,board_id TEXT REFERENCES board(id),kind TEXT,x_offset INTEGER,y_offset INTEGER,options TEXT);
CREATE TABLE layout(id TEXT PRIMARY KEY,name TEXT,board_id TEXT REFERENCES board(id),column_count INTEGER,breakpoint INTEGER,role TEXT);
CREATE TABLE item_layout(item_id TEXT REFERENCES item(id) ON DELETE CASCADE,
section_id TEXT REFERENCES section(id) ON DELETE CASCADE,layout_id TEXT REFERENCES layout(id) ON DELETE CASCADE,
x_offset INTEGER,y_offset INTEGER,width INTEGER,height INTEGER,PRIMARY KEY(item_id,section_id,layout_id));
CREATE TABLE section_layout(section_id TEXT REFERENCES section(id) ON DELETE CASCADE,
layout_id TEXT REFERENCES layout(id) ON DELETE CASCADE,parent_section_id TEXT REFERENCES section(id) ON DELETE CASCADE,
x_offset INTEGER,y_offset INTEGER,width INTEGER,height INTEGER,PRIMARY KEY(section_id,layout_id));
INSERT INTO user VALUES('admin','main','main');
INSERT INTO "group" VALUES('admins','credentials-admin','main',NULL);
INSERT INTO groupMember VALUES('admins','admin');
INSERT INTO serverSetting VALUES('board','{"json":{"homeBoardId":"main","mobileHomeBoardId":null}}');
INSERT INTO board VALUES('main','dashboard',0,'admin',NULL,NULL,'red','orange');
INSERT INTO app VALUES('existing','Existing app','keep','icon','https://existing.example',NULL);
INSERT INTO item VALUES('existing','main','app','{"json":{"appId":"existing"}}','{}');
'''


def app(name='demo'):
    return dict(key='compose:' + name, name=name, hostname=name + sync.SUFFIX, description='Staging app', kind='compose')


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'db').mkdir()
        self.db = sqlite3.connect(self.root / 'db/db.sqlite')
        self.db.executescript(SCHEMA)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def run_sync(self, apps, **kwargs):
        return sync.reconcile(apps, self.root, **kwargs)

    def test_add_update_remove_idempotent_and_preserve_main(self):
        defaults = sync.home_settings(self.db)
        main = self.db.execute("SELECT * FROM board WHERE id='main'").fetchall()
        self.assertTrue(self.run_sync([app()])['changed'])
        self.assertFalse(self.run_sync([app()])['changed'])
        self.assertTrue(self.run_sync([app(), app('next-project')])['changed'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM item_layout').fetchone()[0], 6)
        self.assertTrue(self.run_sync([app('next-project')])['changed'])
        self.assertIsNone(self.db.execute('SELECT id FROM app WHERE id=?', (sync.identifier('a', 'compose:demo'),)).fetchone())
        self.run_sync([])
        self.assertFalse(self.run_sync([])['changed'])
        self.assertEqual(self.db.execute('SELECT id FROM item').fetchall(), [('existing',)])
        self.assertEqual(defaults, sync.home_settings(self.db))
        self.assertEqual(main, self.db.execute("SELECT * FROM board WHERE id='main'").fetchall())
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_check_does_not_write(self):
        self.assertTrue(self.run_sync([app()], check=True)['changed'])
        self.assertFalse((self.root / sync.MANIFEST).exists())
        self.assertEqual(self.db.execute('SELECT count(*) FROM board').fetchone()[0], 1)

    def test_homarr_new_tab_migration_does_not_create_recurring_drift(self):
        self.run_sync([app()])
        for identity, encoded in self.db.execute("SELECT id,options FROM item WHERE id!='existing'"):
            options = json.loads(encoded)
            if 'openInNewTab' in options['json']:
                options['json']['openIn'] = 'newTab' if options['json'].pop('openInNewTab') else 'sameTab'
                self.db.execute('UPDATE item SET options=? WHERE id=?',
                                (json.dumps(options, separators=(',', ':')), identity))
        self.db.commit()
        self.assertFalse(self.run_sync([app()], check=True)['changed'])

    def test_existing_board_requires_explicit_adoption(self):
        self.db.execute("INSERT INTO board(id,name,is_public) VALUES('legacy','Staging',0)")
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'explicit'):
            self.run_sync([app()])
        self.run_sync([app()], adopt='legacy')
        self.assertEqual(json.loads((self.root / sync.MANIFEST).read_text())['board_id'], 'legacy')

    def test_refuses_home_or_public_board(self):
        self.run_sync([app()])
        board = json.loads((self.root / sync.MANIFEST).read_text())['board_id']
        self.db.execute('UPDATE user SET home_board_id=?', (board,))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'home board'):
            self.run_sync([])
        self.db.execute("UPDATE user SET home_board_id='main'")
        self.db.execute('UPDATE board SET is_public=1 WHERE id=?', (board,))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'private'):
            self.run_sync([])

    def test_invalid_host_does_not_remove_existing_tile(self):
        self.run_sync([app()])
        bad = app('evil')
        bad['hostname'] = 'evil.example'
        with self.assertRaises(ValueError):
            self.run_sync([bad])
        self.assertEqual(self.db.execute('SELECT count(*) FROM item').fetchone()[0], 2)

    def test_failed_write_rolls_back(self):
        self.run_sync([app()])
        self.db.executescript("CREATE TRIGGER fail_insert BEFORE INSERT ON app WHEN new.name='fail' BEGIN SELECT RAISE(ABORT,'test'); END;")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sync([app('fail')])
        self.assertFalse(self.run_sync([app()])['changed'])

    def test_shared_app_not_modified(self):
        self.run_sync([app()])
        aid = sync.identifier('a', 'compose:demo')
        self.db.execute('INSERT INTO item(id,board_id,kind,options) VALUES(?,?,?,?)',
                        ('shared','main','app',sync.encoded(dict(appId=aid))))
        self.db.commit()
        changed = app()
        changed['name'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'another board'):
            self.run_sync([changed])
        self.run_sync([])
        self.assertIsNotNone(self.db.execute('SELECT id FROM app WHERE id=?',(aid,)).fetchone())

    def test_discovery_includes_enabled_projects_and_ignores_retained_archives(self):
        staging = self.root / 'staging'
        control = staging / 'symphony/control'
        control.mkdir(parents=True)
        (control / 'routes.json').write_text(json.dumps({
            'owner/new-project': dict(hostname='new-project' + sync.SUFFIX, enabled=True),
            'owner/dummy': dict(hostname='dummy' + sync.SUFFIX, enabled=False),
        }))
        registry = {'film-introspect': dict(hostname='film-introspect' + sync.SUFFIX, repository='https://github.com/owner/film-introspect.git')}
        apps = sync.discover(registry, staging)
        self.assertEqual([a['key'] for a in apps], ['compose:film-introspect','symphony:owner/new-project'])
        (control / 'routes.json').write_text('{broken')
        with self.assertRaises(ValueError):
            sync.discover(registry, staging)


if __name__ == '__main__':
    unittest.main()
