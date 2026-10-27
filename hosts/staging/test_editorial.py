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

    def test_draft_map_replaces_same_identity_git_copy_and_stays_out_of_published(self):
        identity = '11111111-1111-4111-8111-111111111111'
        article = self.base / 'content/interests/topic/subtopic/legacy.mdx'
        article.write_text('---\nid: ' + identity + '\n---\nlegacy')
        maps = self.base / 'content/obsidian'
        (maps / 'legacy').mkdir(parents=True)
        (maps / 'legacy/secret.md').write_text('draft map body')
        (maps / 'collections.json').write_text(json.dumps([{'id':'legacy','directory':'legacy','articleUrl':'/topic/subtopic/map'}]))
        changes = {
            'manifest.json': json.dumps([{'id':identity,'url':'/renamed/moved/map'}]),
            'history.json': json.dumps({identity: {'current':'/renamed/moved/map','paths':['/topic/subtopic/map','/renamed/moved/map']}}),
            'preview/obsidian/collections.json': json.dumps([{'id':'legacy','directory':'legacy','articleUrl':'/renamed/moved/map'}]),
            'preview/obsidian/legacy/Map.md': 'new map',
            'published/obsidian/collections.json': '[]',
        }
        self.files.update(changes)
        sums = {name: hashlib.sha256(value.encode()).hexdigest() for name,value in self.files.items()}
        revision = hashlib.sha256(json.dumps(sums,separators=(',', ':')).encode()).hexdigest()
        source = self.root / revision
        for name,value in self.files.items():
            file=source/name; file.parent.mkdir(parents=True,exist_ok=True); file.write_text(value)
        (source/'checksums.json').write_text(json.dumps(sums))
        target=materialize(self.base,source,self.root/'public-map','published')
        self.assertFalse((target/'content/interests/topic/subtopic/legacy.mdx').exists())
        self.assertFalse((target/'content/obsidian/legacy').exists())
        self.assertEqual(json.loads((target/'content/obsidian/collections.json').read_text()), [])
        self.assertTrue(article.exists())
        preview = materialize(self.base, source, self.root/'preview-map')
        self.assertEqual((preview/'content/obsidian/legacy/Map.md').read_text(), 'new map')
        self.assertFalse((preview/'content/obsidian/legacy/secret.md').exists())

    def test_missing_or_modified_bytes_cannot_deploy(self):
        (self.source / next(iter(self.files))).write_text('modified')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            snapshot(self.root, self.revision)

    def test_parent_and_child_folder_renames_preserve_their_contents(self):
        parent = '11111111-1111-4111-8111-111111111111'
        child = '22222222-2222-4222-8222-222222222222'
        interests = self.base / 'content/interests'
        (interests / 'topic/_index.md').write_text('---\nid: ' + parent + '\n---\n')
        (interests / 'topic/subtopic/_index.md').write_text('---\nid: ' + child + '\n---\n')
        (interests / 'topic/subtopic/retained.md').write_text('Retained article')
        files = {
            'preview/interests/renamed/_index.md': '---\nid: ' + parent + '\n---\n',
            'preview/interests/renamed/moved/_index.md': '---\nid: ' + child + '\n---\n',
            'preview/interests/renamed/moved/new.md': 'New article',
            'history.json': '{}', 'manifest.json': '[]',
        }
        sums = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in files.items()}
        revision = hashlib.sha256(json.dumps(sums, separators=(',', ':')).encode()).hexdigest()
        source = self.root / revision
        for name, value in files.items():
            file = source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(value)
        (source / 'checksums.json').write_text(json.dumps(sums))
        target = materialize(self.base, source, self.root / 'renamed-context')
        self.assertEqual((target / 'content/interests/renamed/moved/retained.md').read_text(), 'Retained article')
        self.assertEqual((target / 'content/interests/renamed/moved/new.md').read_text(), 'New article')
        self.assertFalse((target / 'content/interests/topic').exists())
        self.assertTrue((interests / 'topic/subtopic/retained.md').exists())

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
