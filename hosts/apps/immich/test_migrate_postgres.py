import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('migration', Path(__file__).with_name('migrate-postgres.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RestoreListTest(unittest.TestCase):
    def test_omits_only_legacy_extension_ddl_never_table_data(self):
        keep = ['; Archive comment', '4; 0 0 EXTENSION - vector',
                '7; 0 0 COMMENT - EXTENSION vector',
                '20; 0 0 TABLE DATA public vectors postgres',
                '21; 0 0 INDEX public face_index postgres']
        omit = ['1; 0 0 SCHEMA - vectors postgres', '2; 0 0 EXTENSION - vectors',
                '3; 0 0 COMMENT - EXTENSION vectors']
        self.assertEqual(module.retained_toc('\n'.join(keep + omit)), '\n'.join(keep) + '\n')


if __name__ == '__main__':
    unittest.main()
