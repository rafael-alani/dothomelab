#!/usr/bin/env python3
"""Isolated fixtures for the manual photo archive audit; no cloud access."""
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    'photo_audit', Path(__file__).resolve().parents[1] / 'audit-photo-archive.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
GNU_TAR = b'GNU tar' in subprocess.run(
    ['tar', '--version'], capture_output=True, check=True).stdout


class PhotoAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.source = root / 'source'
        self.stage = root / 'stage'
        self.source.mkdir()
        self.stage.mkdir()
        (self.source / 'photo.jpg').write_bytes(b'original-photo' * 100)
        os.link(self.source / 'photo.jpg', self.source / 'hardlink.jpg')
        (self.source / 'link').symlink_to('photo.jpg')
        # Python's PAX timestamp float can round nanoseconds differently from GNU tar.
        os.utime(self.source / 'photo.jpg', (1700000000, 1700000000))
        self.build()

    def build(self, duplicate=False):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
            tar.add(self.source, arcname='.')
            if duplicate:
                tar.add(self.source, arcname='.')
        for p in self.stage.iterdir():
            p.unlink()
        data = buffer.getvalue()
        for number, offset in enumerate(range(0, len(data), 1024)):
            (self.stage / f'archive.tar.part-{number:05d}').write_bytes(data[offset:offset + 1024])

    def test_complete_split_archive_including_links(self):
        result = audit.audit(self.source, self.stage)
        self.assertTrue(result['passed'])
        self.assertEqual(result['source_files'], 2)
        self.assertEqual(result['source_symlinks'], 1)

    def test_missing_file_in_archive(self):
        (self.source / 'new.jpg').write_bytes(b'new')
        result = audit.audit(self.source, self.stage)
        self.assertFalse(result['passed'])
        self.assertEqual(result['missing_paths'], 1)

    def test_unexpected_file_in_archive(self):
        (self.source / 'link').unlink()
        result = audit.audit(self.source, self.stage)
        self.assertFalse(result['passed'])
        self.assertEqual(result['unexpected_paths'], 1)

    def test_duplicate_paths(self):
        self.build(duplicate=True)
        result = audit.audit(self.source, self.stage)
        self.assertFalse(result['passed'])
        self.assertGreater(result['duplicate_archive_paths'], 0)

    def test_missing_part(self):
        (self.stage / 'archive.tar.part-00001').unlink()
        with self.assertRaises(ValueError):
            audit.audit(self.source, self.stage)

    def test_missing_source_and_walk_errors_fail(self):
        with self.assertRaises(ValueError):
            audit.inventory(self.source / 'absent')
        def unreadable(*args, **kwargs):
            kwargs['onerror'](PermissionError('fixture'))
        with mock.patch.object(audit.os, 'walk', side_effect=unreadable):
            with self.assertRaises(PermissionError):
                audit.inventory(self.source)

    @unittest.skipUnless(GNU_TAR, 'full-content comparison requires Linux/GNU tar')
    def test_contents_detect_same_size_change(self):
        self.assertTrue(audit.audit(self.source, self.stage, contents=True)['passed'])
        photo = self.source / 'photo.jpg'
        original = photo.stat()
        photo.write_bytes(b'changed--photo' * 100)
        os.utime(photo, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.assertTrue(audit.audit(self.source, self.stage)['passed'])
        result = audit.audit(self.source, self.stage, contents=True)
        self.assertFalse(result['passed'])
        self.assertNotEqual(result['content_comparison']['tar_exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
