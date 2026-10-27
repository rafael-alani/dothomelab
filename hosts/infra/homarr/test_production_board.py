"""Exercise board ownership and idempotence against a disposable Homarr schema."""
from pathlib import Path
import runpy
import sqlite3
import unittest

HERE = Path(__file__).resolve().parent
SCHEMA = runpy.run_path(str(HERE.parents[1] / 'staging/test_sync_homarr.py'))['SCHEMA']
SQL = (HERE / 'reconcile-production.sql').read_text()


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript(SCHEMA)

    def tearDown(self):
        self.db.close()

    def test_repeat_preserves_other_boards_defaults_and_user_layout(self):
        before = {t: self.db.execute('SELECT * FROM "' + t + '"').fetchall()
                  for t in ('user', 'group', 'serverSetting')}
        self.db.executescript(SQL)
        self.db.execute("UPDATE item_layout SET x_offset=3 WHERE layout_id='dhlproductiondesktop01'")
        self.db.commit()
        self.db.executescript(SQL)
        self.assertEqual(self.db.execute("SELECT href FROM app WHERE id='dhlproductionblogapp001'").fetchone(), ('https://rafael.ink',))
        self.assertEqual(self.db.execute('SELECT count(*) FROM item_layout').fetchone(), (3,))
        self.assertEqual(self.db.execute("SELECT x_offset FROM item_layout WHERE layout_id='dhlproductiondesktop01'").fetchone(), (3,))
        self.assertEqual(self.db.execute("SELECT id FROM item WHERE board_id='main'").fetchall(), [('existing',)])
        for table, rows in before.items():
            self.assertEqual(self.db.execute('SELECT * FROM "' + table + '"').fetchall(), rows)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_refuses_existing_user_board_or_public_managed_board(self):
        for identity, public in [('user-board', 0), ('dhlproductionboard00001', 1)]:
            with self.subTest(identity=identity):
                self.db.execute('INSERT INTO board(id,name,is_public) VALUES(?,?,?)', (identity, 'Production', public))
                self.db.commit()
                with self.assertRaises(sqlite3.IntegrityError):
                    self.db.executescript(SQL)
                self.db.rollback()
                self.assertIsNone(self.db.execute("SELECT id FROM app WHERE id='dhlproductionblogapp001'").fetchone())
                self.db.execute('DELETE FROM board WHERE id=?', (identity,))
                self.db.commit()


if __name__ == '__main__':
    unittest.main()
