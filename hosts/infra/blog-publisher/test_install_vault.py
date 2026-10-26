"""About migration preserves prior files and never overwrites authored prose."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('installer', Path(__file__).with_name('install-vault.py'))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class AboutMigrationTest(unittest.TestCase):
    def test_seed_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, repo = root / 'vault', root / 'repo'
            target = vault / 'Blog/about'
            source = repo / 'content/interests/about'
            target.mkdir(parents=True)
            source.mkdir(parents=True)
            metadata = '---\ntitle: About\n---\n'
            waypoint = '%% Begin Waypoint %%\n- [_index](./_index.md)\n%% End Waypoint %%\n'
            (target / '_index.md').write_text(metadata)
            (target / 'about.md').write_text(waypoint)
            (source / '_index.md').write_text(metadata + '\nExisting biography.\n')
            installer.seed_about(vault, repo)
            self.assertEqual((target / 'about.md').read_text(), 'Existing biography.\n')
            self.assertIn('![[about]]', (target / '_index.md').read_text())
            backup, = (vault / '.blog-publisher-backups').iterdir()
            self.assertEqual((backup / '_index.md').read_text(), metadata)
            self.assertEqual((backup / 'about.md').read_text(), waypoint)
            with self.assertRaisesRegex(ValueError, 'already has content'):
                installer.seed_about(vault, repo)
            (target / '_index.md').write_text(metadata)
            with self.assertRaisesRegex(ValueError, 'already has content'):
                installer.seed_about(vault, repo)


if __name__ == '__main__':
    unittest.main()
