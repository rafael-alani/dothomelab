from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SYNC = HERE / "sync-pinepods-to-echo.py"
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


@unittest.skipUnless(FFMPEG and FFPROBE, "FFmpeg is required")
class PinePodsEchoSyncTests(unittest.TestCase):
    def make_audio(self, path: Path, disguised_video: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if disguised_video:
            command = [
                FFMPEG,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=16x16:d=0.25",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:duration=0.25",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-f",
                "mp4",
                str(path),
            ]
        else:
            command = [
                FFMPEG,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=0.25",
                "-c:a",
                "libmp3lame",
                str(path),
            ]
        subprocess.run(command, check=True)

    def run_sync(
        self,
        source: Path,
        device: Path,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SYNC),
                "--source",
                str(source),
                "--device",
                str(device),
                "--min-free-percent",
                "0",
                *extra,
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def probe_output(self, path: Path) -> dict:
        completed = subprocess.run(
            [
                FFPROBE,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,codec_type:format_tags=title,artist,album,album_artist,genre",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        return json.loads(completed.stdout)

    def test_compiles_delta_syncs_retains_and_explicitly_prunes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            source = temp / "pinepods"
            device = temp / "ECHO"
            device.mkdir()
            first = (
                source
                / "Example Show"
                / "2026-07-01_First Episode_2_101.mp3"
            )
            second = (
                source
                / "Example Show"
                / "2026-07-02_Second Episode_2_102.mp3"
            )
            self.make_audio(first)
            self.make_audio(second, disguised_video=True)

            initial = self.run_sync(source, device)
            self.assertEqual(
                initial.returncode,
                0,
                initial.stdout + initial.stderr,
            )
            self.assertIn("added=2", initial.stdout)
            outputs = sorted((device / "Podcasts" / "PinePods").rglob("*.mp3"))
            self.assertEqual(len(outputs), 2)
            for output in outputs:
                probe = self.probe_output(output)
                streams = probe["streams"]
                self.assertEqual(
                    [
                        stream["codec_name"]
                        for stream in streams
                        if stream["codec_type"] == "audio"
                    ],
                    ["mp3"],
                )
                self.assertEqual(
                    [
                        stream
                        for stream in streams
                        if stream["codec_type"] == "video"
                    ],
                    [],
                )
                tags = probe["format"]["tags"]
                self.assertEqual(tags["artist"], "Example Show")
                self.assertEqual(tags["album"], "Example Show")
                self.assertEqual(tags["album_artist"], "* PODCASTS *")
                self.assertEqual(tags["genre"], "Podcast")

            manifest_path = device / ".pinepods-echo.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["episodes"]), 2)

            second_run = self.run_sync(source, device)
            self.assertEqual(second_run.returncode, 0)
            self.assertIn(
                "added=0 updated=0 unchanged=2 retained=0 pruned=0",
                second_run.stdout,
            )

            first.unlink()
            retained = self.run_sync(source, device)
            self.assertEqual(retained.returncode, 0)
            self.assertIn("unchanged=1 retained=1 pruned=0", retained.stdout)
            self.assertEqual(
                len(list((device / "Podcasts" / "PinePods").rglob("*.mp3"))),
                2,
            )

            pruned = self.run_sync(source, device, "--prune")
            self.assertEqual(pruned.returncode, 0)
            self.assertIn("unchanged=1 retained=0 pruned=1", pruned.stdout)
            self.assertEqual(
                len(list((device / "Podcasts" / "PinePods").rglob("*.mp3"))),
                1,
            )

    def test_dry_run_does_not_initialize_device(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            source = temp / "pinepods"
            device = temp / "ECHO"
            device.mkdir()
            episode = source / "Show" / "2026-07-03_Test_2_103.mp3"
            self.make_audio(episode)

            result = self.run_sync(source, device, "--dry-run")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("dry-run summary", result.stdout)
            self.assertFalse((device / ".pinepods-echo.json").exists())
            self.assertFalse((device / "Podcasts").exists())

    def test_unicode_metadata_and_filename_are_preserved_but_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            source = temp / "pinepods"
            device = temp / "ECHO"
            device.mkdir()
            title = "中文播客标题" * 10
            episode = source / "中文学习" / f"2026-07-04_{title}_2_104.mp3"
            self.make_audio(episode)

            result = self.run_sync(source, device)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            outputs = list(
                (device / "Podcasts" / "PinePods" / "中文学习").glob("*.mp3")
            )
            self.assertEqual(len(outputs), 1)
            self.assertLessEqual(len(outputs[0].name.encode("utf-8")), 180)
            tags = self.probe_output(outputs[0])["format"]["tags"]
            self.assertEqual(tags["artist"], "中文学习")
            self.assertTrue(tags["title"].startswith("中文播客标题"))


if __name__ == "__main__":
    unittest.main()
