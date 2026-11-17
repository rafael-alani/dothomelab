import gzip
from pathlib import Path
import subprocess
import tempfile
import unittest


PATCH = Path(__file__).with_name("patch-photo-links.sh")
ORIGINAL = b'let a=Q(()=>`https://my.immich.app/photos/${t.id}`);'
EXPECTED = ORIGINAL.replace(b"my.immich.app", b"pictures.rafael.ink")


class PhotoLinksTest(unittest.TestCase):
    def test_patch_survives_restart_and_replaces_compressed_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "_app/immutable/nodes/2.example.js"
            bundle.parent.mkdir(parents=True)
            bundle.write_bytes(ORIGINAL)
            compressed = Path(str(bundle) + ".gz")
            compressed.write_bytes(gzip.compress(ORIGINAL))
            brotli = Path(str(bundle) + ".br")
            brotli.write_bytes(b"stale precompressed bundle")
            for _ in range(2):
                subprocess.run(["sh", str(PATCH), directory], check=True)
                self.assertEqual(bundle.read_bytes(), EXPECTED)
                self.assertEqual(gzip.decompress(compressed.read_bytes()), EXPECTED)
                self.assertFalse(brotli.exists())

    def test_changed_upstream_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "changed.js").write_text("upstream changed the link builder")
            result = subprocess.run(["sh", str(PATCH), directory], capture_output=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
