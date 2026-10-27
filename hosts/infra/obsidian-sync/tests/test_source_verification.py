#!/usr/bin/env python3
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location(
    "source_verification", Path(__file__).resolve().parents[1] / "source-verification.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class SourceVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.generation = self.root / "generation"
        self.source.mkdir()
        self.generation.mkdir()
        (self.source / "a.jpg").write_bytes(b"A" * 6000)
        (self.source / "b.jpg").write_bytes(b"B" * 6000)
        (self.source / "space ü\nname.jpg").write_bytes(b"other")
        (self.source / "empty").mkdir()

    def inventory(self, dataset="photos"):
        with contextlib.redirect_stdout(io.StringIO()):
            v.inventory(self.source, dataset, self.generation / v.INVENTORY)

    def parts(self, raw):
        for p in self.generation.glob("archive.tar.part-*"):
            p.unlink()
        lines = []
        for i, start in enumerate(range(0, len(raw), 2048)):
            data = raw[start:start + 2048]
            name = f"archive.tar.part-{i:05d}"
            (self.generation / name).write_bytes(data)
            lines.append(hashlib.sha256(data).hexdigest() + "  " + name + "\n")
        (self.generation / "SHA256SUMS").write_text("".join(lines))

    def archive(self, omit=None, duplicate=False, dataset="photos"):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for root in v.roots_for(dataset):
                archive.add(self.source / root, arcname="./" + root if root != "." else ".",
                            filter=lambda member: None if member.name == omit else member)
            if duplicate:
                archive.add(self.source / "a.jpg", arcname="./a.jpg")
        self.parts(raw.getvalue())
        return raw.getvalue()

    def verify(self, dataset="photos", source=True):
        with contextlib.redirect_stdout(io.StringIO()):
            v.verify(self.generation, dataset, self.source if source else None)

    def test_every_file_crossing_parts_and_unusual_names(self):
        os.link(self.source / "a.jpg", self.source / "hardlink.jpg")
        self.inventory()
        self.archive()
        self.verify()
        v.check(self.generation, "photos")
        receipt = json.loads((self.generation / v.RECEIPT).read_text())
        self.assertEqual(receipt["files"], 4)
        self.assertEqual(receipt["bytes"], 18005)

    def test_same_size_wrong_contents_fail_even_with_new_part_checksums(self):
        self.inventory()
        (self.source / "b.jpg").write_bytes(b"A" * 6000)
        self.archive()
        with self.assertRaisesRegex(v.InvalidBackup, "SHA-256 mismatch"):
            self.verify(source=False)

    def test_missing_file(self):
        self.inventory()
        self.archive(omit="./b.jpg")
        with self.assertRaisesRegex(v.InvalidBackup, "missing source paths"):
            self.verify()

    def test_duplicate_member(self):
        self.inventory()
        self.archive(duplicate=True)
        with self.assertRaisesRegex(v.InvalidBackup, "Repeated archive path"):
            self.verify()

    def test_unexpected_member(self):
        self.inventory()
        (self.source / "extra.jpg").write_bytes(b"extra")
        self.archive()
        with self.assertRaisesRegex(v.InvalidBackup, "unexpected path"):
            self.verify()

    def test_changed_source_after_archive(self):
        self.inventory()
        self.archive()
        (self.source / "b.jpg").write_bytes(b"C" * 6000)
        with self.assertRaisesRegex(v.InvalidBackup, "Source changed"):
            self.verify()

    def test_added_source_after_archive(self):
        self.inventory()
        self.archive()
        (self.source / "new.jpg").write_bytes(b"new")
        with self.assertRaisesRegex(v.InvalidBackup, "Source changed"):
            self.verify()

    def test_source_changes_during_hashing(self):
        original = v.digest
        def changing_digest(stream):
            result = original(stream)
            (self.source / "new.jpg").write_bytes(b"new")
            return result
        with mock.patch.object(v, "digest", side_effect=changing_digest):
            with self.assertRaisesRegex(v.InvalidBackup, "Source changed"):
                self.inventory()
        self.assertFalse((self.generation / v.INVENTORY).exists())

    def test_symlink_rejected_instead_of_silently_omitted(self):
        (self.source / "linked.jpg").symlink_to(self.source / "a.jpg")
        with self.assertRaisesRegex(v.InvalidBackup, "symlink"):
            self.inventory()

    def test_truncated_end(self):
        self.inventory()
        raw = self.archive()
        self.parts(raw[:-1])
        with self.assertRaisesRegex(v.InvalidBackup, "Truncated"):
            self.verify()

    def test_hidden_second_archive(self):
        self.inventory()
        raw = self.archive()
        self.parts(raw + raw)
        with self.assertRaisesRegex(v.InvalidBackup, "after archive end"):
            self.verify()

    def test_repeated_part(self):
        self.inventory()
        raw = self.archive()
        self.parts(raw[:2048] + raw[:2048] + raw[4096:])
        with self.assertRaises((v.InvalidBackup, tarfile.TarError)):
            self.verify()

    def test_part_gap_and_duplicate_checksum_entry(self):
        self.inventory()
        self.archive()
        checks = self.generation / "SHA256SUMS"
        lines = checks.read_text().splitlines(True)
        for bad in [lines[:1] + lines[2:], lines[:1] + lines]:
            checks.write_text("".join(bad))
            with self.assertRaisesRegex(v.InvalidBackup, "contiguous"):
                v.parts_for(self.generation)

    def test_receipt_binds_inventory_and_chunk_checksums(self):
        self.inventory()
        self.archive()
        self.verify()
        p = self.generation / "SHA256SUMS"
        s = p.read_text()
        p.write_text(("1" if s[0] != "1" else "2") + s[1:])
        with self.assertRaisesRegex(v.InvalidBackup, "receipt no longer matches"):
            v.check(self.generation, "photos")

    def test_immich_only_archives_declared_original_roots(self):
        for name in ("upload", "library", "thumbs"):
            (self.source / name).mkdir()
            (self.source / name / "photo.jpg").write_bytes(name.encode())
        self.inventory("immich")
        self.archive(dataset="immich")
        self.verify("immich")
        receipt = json.loads((self.generation / v.RECEIPT).read_text())
        self.assertEqual(receipt["files"], 2)


if __name__ == "__main__":
    unittest.main()
