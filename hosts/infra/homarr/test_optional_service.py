"""Verify disabling GPT removes its tiles and retains unrelated dashboard state."""
from pathlib import Path
import runpy
import sqlite3
import unittest

HERE = Path(__file__).resolve().parent
SCHEMA = runpy.run_path(str(HERE.parents[1] / 'staging/test_sync_homarr.py'))['SCHEMA']


class OptionalServiceTests(unittest.TestCase):
    def test_disable_is_scoped_and_repeatable(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            db.execute("INSERT INTO app(id,name) VALUES ('dhlpaperlessgptapp000001','Paperless-GPT')")
            db.execute("INSERT INTO integration(id,app_id) VALUES ('gpt-integration','dhlpaperlessgptapp000001')")
            db.execute('INSERT INTO item(id,board_id,kind,options) VALUES(?,?,?,?)',
                       ('gpt-tile', 'main', 'app', '{"json":{"appId":"dhlpaperlessgptapp000001"}}'))
            db.commit()
            sql = (HERE / 'disable-paperless-gpt.sql').read_text()
            db.executescript(sql)
            db.executescript(sql)
            self.assertEqual(db.execute('SELECT id FROM app').fetchall(), [('existing',)])
            self.assertEqual(db.execute('SELECT id FROM item').fetchall(), [('existing',)])
            self.assertEqual(db.execute('SELECT app_id FROM integration').fetchall(), [(None,)])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])


if __name__ == '__main__':
    unittest.main()
