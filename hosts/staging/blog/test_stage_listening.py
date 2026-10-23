#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('stage_listening', Path(__file__).with_name('stage-listening.py'))
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)


class ListeningCopyTest(unittest.TestCase):
    def test_copy_is_verified_idempotent_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.mp3'
            source.write_bytes(b'isolated test audio')
            target = staging.stage_track(source, root / 'copies', 'Song', 'Artist')
            self.assertEqual((target / 'audio.mp3').read_bytes(), source.read_bytes())
            self.assertEqual(staging.stage_track(source, root / 'copies', 'Song', 'Artist'), target)
            with self.assertRaises(ValueError):
                staging.stage_track(source, root / 'copies', 'Other song', 'Artist')
            (target / 'audio.mp3').write_bytes(b'corruption')
            with self.assertRaises(ValueError):
                staging.stage_track(source, root / 'copies', 'Song', 'Artist')
            self.assertEqual(source.read_bytes(), b'isolated test audio')


if __name__ == '__main__':
    unittest.main()
