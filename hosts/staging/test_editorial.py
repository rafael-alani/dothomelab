#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from editorial import snapshot, materialize


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'base'
        (self.base / 'content/interests/topic/subtopic').mkdir(parents=True)
        (self.base / 'content/route-history.json').write_text('{}')
        self.files = {'preview/interests/topic/subtopic/draft.md': 'draft body',
                      'published/interests/topic/subtopic/ready.md': 'public body',
                      'preview/interests/topic/subtopic/ready.md': 'public body',
                      'history.json': '{}', 'manifest.json': '[]'}
        self.sums = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in self.files.items()}
        self.revision = hashlib.sha256(json.dumps(self.sums, separators=(',', ':')).encode()).hexdigest()
        self.source = self.root / self.revision
        for name, value in self.files.items():
            file = self.source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(value)
        (self.source / 'checksums.json').write_text(json.dumps(self.sums))

    def test_preview_and_public_are_separate_and_source_is_unchanged(self):
        for mode, expected in [('preview', {'draft.md', 'ready.md'}), ('published', {'ready.md'})]:
            target = materialize(self.base, self.source, self.root / mode, mode)
            self.assertEqual({p.name for p in (target / 'content/interests/topic/subtopic').iterdir()}, expected)
            self.assertEqual(materialize(self.base, self.source, target, mode), target)
        self.assertEqual(list((self.base / 'content/interests/topic/subtopic').iterdir()), [])

    def test_missing_or_modified_bytes_cannot_deploy(self):
        (self.source / next(iter(self.files))).write_text('modified')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            snapshot(self.root, self.revision)

    def test_extra_files_or_symlinks_cannot_enter_build(self):
        (self.source / 'secret').write_text('must not be exported')
        with self.assertRaisesRegex(ValueError, 'Unexpected file'):
            snapshot(self.root, self.revision)

    def test_existing_repository_article_is_never_overwritten(self):
        (self.base / 'content/interests/topic/subtopic/draft.md').write_text('existing')
        with self.assertRaisesRegex(ValueError, 'collides'):
            materialize(self.base, self.source, self.root / 'collision')


if __name__ == '__main__':
    unittest.main()
