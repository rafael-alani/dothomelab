import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('blog_build', Path(__file__).with_name('build.py'))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class EditorialInputTests(unittest.TestCase):
    def test_review_stays_private_and_pinned_until_live_input_is_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            revision = 'a' * 64
            for name, value in [('editorial', {'revision': 'live'}), ('review-editorial', {'revision': revision})]:
                (root / name).mkdir()
                (root / name / 'current.json').write_text(json.dumps(value))
            (root / 'review-editorial' / revision).mkdir()
            (root / 'review-editorial' / revision / 'checksums.json').write_text('{}')
            selected = build.editorial_input(root, 'staging', revision)
            self.assertEqual(selected, (root / 'review-editorial', {'revision': revision}))
            self.assertEqual(build.editorial_input(root, 'staging'), selected)
            self.assertEqual(build.editorial_input(root, 'production'), (root / 'editorial', {'revision': 'live'}))
            for invalid in ['../private', 'b' * 64]:
                with self.assertRaises(ValueError):
                    build.editorial_input(root, 'staging', invalid)
                self.assertEqual(build.editorial_input(root, 'staging'), selected)
            with self.assertRaisesRegex(ValueError, 'staging-only'):
                build.editorial_input(root, 'production', revision)
            self.assertEqual(build.editorial_input(root, 'staging', live_input=True), (root / 'editorial', {'revision': 'live'}))
            self.assertTrue((root / 'review-editorial' / revision).is_dir())


if __name__ == '__main__':
    unittest.main()
