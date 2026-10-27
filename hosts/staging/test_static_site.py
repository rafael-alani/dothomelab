"""Static publication must not require an optional Obsidian section."""
from pathlib import Path
import tempfile
import unittest

from static_site import activate


class StaticSiteTests(unittest.TestCase):
    def test_complete_homepage_can_publish_without_about(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / 'release'
            release.mkdir()

            def run(*args, **kwargs):
                if '--images' in args:
                    return 'fixture-image'
                if args[:2] == ('docker', 'create'):
                    return 'fixture-container'
                if args[:2] == ('docker', 'cp'):
                    destination = Path(args[-1])
                    if destination.name == 'client':
                        destination.mkdir()
                        (destination / 'index.html').write_text('Home')
                    else:
                        destination.write_text('')

            activate(root, release, run)
            current = root / 'static-site/current'
            self.assertEqual((current / 'client/index.html').read_text(), 'Home')
            self.assertFalse((current / 'client/about').exists())


if __name__ == '__main__':
    unittest.main()
