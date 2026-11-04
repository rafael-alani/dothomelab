import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os
import subprocess

from audit import verify_asset, probe_video, probe_valid


class IntegrityAuditTests(unittest.TestCase):
    def test_probe_resets_real_descriptor_after_buffered_signature_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'video'
            path.write_bytes(b'header' + b'x' * 8192)
            with path.open('rb') as stream:
                stream.read(16)
                stream.seek(0)
                def run(command, stdin, **kwargs):
                    self.assertEqual(os.read(stdin.fileno(), 6), b'header')
                    return subprocess.CompletedProcess(command, 0,
                        b'{"streams":[{"codec_type":"video"}],"format":{"duration":"1"}}', b'')
                with patch('audit.subprocess.run', side_effect=run):
                    self.assertTrue(probe_valid(probe_video(stream)))

    def test_reads_bytes_and_detects_corruption_without_modifying_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'objects').mkdir()
            body = b'\xff\xd8\xfffixture'
            digest = hashlib.sha256(body).hexdigest()
            path = root / 'objects' / (digest + '.jpg')
            path.write_bytes(body)
            path.chmod(0o444)
            asset = {'id': digest, 'path': str(path.relative_to(root)), 'bytes': len(body)}
            self.assertEqual(verify_asset(root, asset)['errors'], [])
            path.chmod(0o644)
            path.write_bytes(body + b'changed')
            errors = verify_asset(root, asset)['errors']
            self.assertIn('hash_mismatch', errors)
            self.assertIn('size_mismatch', errors)
            self.assertIn('writable', errors)
            self.assertEqual(path.read_bytes(), body + b'changed')

    def test_rejects_missing_symlink_and_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'objects').mkdir()
            relative = 'objects/' + 'a' * 64 + '.mp4'
            asset = {'id': 'a' * 64, 'path': relative, 'bytes': 1}
            self.assertIn('FileNotFoundError', verify_asset(root, asset)['errors'])
            (root / relative).symlink_to('/etc/passwd')
            self.assertEqual(verify_asset(root, asset)['errors'], ['symlink'])
            asset['path'] = '../outside'
            self.assertEqual(verify_asset(root, asset)['errors'], ['unsafe_path'])
