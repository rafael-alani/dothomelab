from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
INSTALLER = HERE / "install-hifimule-profile.py"
PROFILE = HERE / "hifimule-profile.json"


class ProfileInstallerTests(unittest.TestCase):
    def run_installer(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "--profile-file",
                str(PROFILE),
                "--profiles-file",
                str(target),
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def test_adds_profile_with_backup_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            target = temp / "device-profiles.json"
            target.write_text(
                json.dumps(
                    {
                        "profiles": [
                            {
                                "id": "passthrough",
                                "name": "Passthrough",
                                "description": "No conversion",
                                "deviceProfile": None,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            first = self.run_installer(target)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            document = json.loads(target.read_text(encoding="utf-8"))
            ids = [profile["id"] for profile in document["profiles"]]
            self.assertEqual(ids, ["passthrough", "snowsky-echo-lossless"])
            backups = list(temp.glob("device-profiles.json.backup-*"))
            self.assertEqual(len(backups), 1)

            second = self.run_installer(target)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("already current", second.stdout)
            self.assertEqual(
                list(temp.glob("device-profiles.json.backup-*")),
                backups,
            )

    def test_replaces_one_stale_profile_without_reordering(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            target = temp / "device-profiles.json"
            target.write_text(
                json.dumps(
                    {
                        "profiles": [
                            {"id": "first"},
                            {
                                "id": "snowsky-echo-lossless",
                                "name": "stale",
                            },
                            {"id": "last"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_installer(target)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            document = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(
                [profile["id"] for profile in document["profiles"]],
                ["first", "snowsky-echo-lossless", "last"],
            )
            expected = json.loads(PROFILE.read_text(encoding="utf-8"))
            self.assertEqual(document["profiles"][1], expected)

    def test_refuses_duplicate_target_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            target = temp / "device-profiles.json"
            target.write_text(
                json.dumps(
                    {
                        "profiles": [
                            {"id": "snowsky-echo-lossless"},
                            {"id": "snowsky-echo-lossless"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_installer(target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate profile id", result.stdout)
            self.assertEqual(
                list(temp.glob("device-profiles.json.backup-*")),
                [],
            )


if __name__ == "__main__":
    unittest.main()
