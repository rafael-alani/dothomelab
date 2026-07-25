#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("reconciler.py")
SPEC = importlib.util.spec_from_file_location("storyteller_reconciler", MODULE_PATH)
assert SPEC and SPEC.loader
reconciler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reconciler)


class ReconcilerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ebooks = self.root / "ebooks"
        self.audio = self.root / "audiobooks"
        self.inbox = self.root / "storyteller" / "inbox"
        self.library = self.root / "storyteller" / "library"
        self.state = self.root / "state"
        for path in (
            self.ebooks,
            self.audio,
            self.inbox,
            self.library,
            self.state,
        ):
            path.mkdir(parents=True)
        self.args = argparse.Namespace(
            ebook_root=str(self.ebooks),
            audiobook_root=str(self.audio),
            inbox=str(self.inbox),
            library=str(self.library),
            state_root=str(self.state),
            database=str(self.root / "missing.db"),
            max_items=1,
            min_free_gib=0,
            copy_headroom_gib=0,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add_pair(self, key: str = "Lewis Carroll/Alice") -> None:
        ebook = self.ebooks / key
        audiobook = self.audio / key / "audio"
        ebook.mkdir(parents=True)
        audiobook.mkdir(parents=True)
        (ebook / "Alice.epub").write_bytes(b"PK\x03\x04public-domain-epub")
        (audiobook / "01.mp3").write_bytes(b"ID3chapter-one")
        (audiobook / "02.mp3").write_bytes(b"ID3chapter-two")

    def manifest(self) -> dict:
        return json.loads((self.state / "manifest.json").read_text())

    def test_stages_once_and_flattens_multifile_audio(self) -> None:
        self.add_pair()
        first = reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(first["staged"], 1)
        staged = self.inbox / "Lewis Carroll/Alice"
        self.assertEqual(
            sorted(path.name for path in staged.iterdir()),
            ["Alice.epub", "audio - 01.mp3", "audio - 02.mp3"],
        )
        self.assertFalse((self.inbox / ".staging").exists())
        self.assertTrue((self.inbox.parent / ".staging").is_dir())
        second = reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(second["unchanged"], 1)
        item = self.manifest()["items"]["Lewis Carroll/Alice"]
        self.assertEqual(item["attempts"], 1)
        self.assertEqual(item["stage_state"], "published")

    def test_ambiguous_epubs_are_reported_not_staged(self) -> None:
        self.add_pair("Test Author/Ambiguous")
        (self.ebooks / "Test Author/Ambiguous/Other.epub").write_bytes(b"other")
        result = reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(result["skipped"], 1)
        self.assertFalse((self.inbox / "Test Author/Ambiguous").exists())
        item = self.manifest()["items"]["Test Author/Ambiguous"]
        self.assertEqual(item["stage_state"], "ambiguous")

    def test_low_space_is_reported_without_copy(self) -> None:
        self.add_pair()
        self.args.min_free_gib = 10**12
        result = reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(result["low_space"], 1)
        self.assertFalse((self.inbox / "Lewis Carroll/Alice").exists())
        self.assertEqual(
            self.manifest()["items"]["Lewis Carroll/Alice"]["stage_state"],
            "low-space",
        )

    def test_changed_sources_do_not_restage(self) -> None:
        self.add_pair()
        reconciler.reconcile(self.args, dry_run=False)
        staged = self.inbox / "Lewis Carroll/Alice"
        for path in staged.iterdir():
            path.unlink()
        staged.rmdir()
        reconciler.reconcile(self.args, dry_run=False)
        source = self.ebooks / "Lewis Carroll/Alice/Alice.epub"
        source.write_bytes(source.read_bytes() + b"changed")
        result = reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(result["changed"], 1)
        self.assertFalse(staged.exists())

    def test_unsafe_key_is_skipped(self) -> None:
        self.add_pair(".hidden/Alice")
        result = reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(result["skipped"], 1)
        self.assertFalse((self.inbox / ".hidden/Alice").exists())

    def test_wud_guard_blocks_reconciliation_until_released(self) -> None:
        self.add_pair()
        self.assertEqual(reconciler.wud_acquire(self.args), 0)
        with self.assertRaisesRegex(RuntimeError, "WUD update guard"):
            reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(reconciler.wud_release(self.args), 0)
        self.assertEqual(reconciler.reconcile(self.args, dry_run=False)["staged"], 1)

    def test_wud_guard_refuses_pending_inbox_work(self) -> None:
        pending = self.inbox / "Pending Author/Pending Book"
        pending.mkdir(parents=True)
        (pending / "Pending.epub").write_bytes(b"pending")
        self.assertEqual(reconciler.wud_acquire(self.args), 75)
        self.assertFalse((self.state / "wud-update.lock").exists())

    def test_existing_pair_does_not_starve_next_pair(self) -> None:
        self.add_pair("A Author/A Existing")
        reconciler.reconcile(self.args, dry_run=False)
        self.add_pair("B Author/B New")
        result = reconciler.reconcile(self.args, dry_run=False)
        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["staged"], 1)
        self.assertTrue((self.inbox / "B Author/B New").is_dir())


if __name__ == "__main__":
    unittest.main()
