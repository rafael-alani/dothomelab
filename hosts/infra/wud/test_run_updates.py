#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("run-updates.py")
SPEC = importlib.util.spec_from_file_location("wud_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class StorytellerGuardTest(unittest.TestCase):
    def candidate(self) -> dict[str, object]:
        return {
            "id": "apps.storyteller",
            "name": "storyteller",
            "watcher": "apps",
            "result": {"tag": "latest"},
        }

    @mock.patch.object(runner.subprocess, "run")
    def test_busy_exit_is_a_safe_false(self, run: mock.Mock) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=75, stdout="BUSY alignment", stderr=""
        )
        self.assertFalse(runner.storyteller_guard("wud-acquire"))

    @mock.patch.object(runner, "api_request")
    @mock.patch.object(runner, "docker_inspect")
    @mock.patch.object(runner, "associated_with_trigger", return_value=True)
    @mock.patch.object(runner, "storyteller_guard", return_value=False)
    def test_busy_candidate_is_not_triggered(
        self,
        guard: mock.Mock,
        _associated: mock.Mock,
        inspect: mock.Mock,
        api: mock.Mock,
    ) -> None:
        inspect.return_value = {
            "Id": "old-container",
            "Image": "old-image",
            "Config": {"Image": "storyteller:latest"},
        }
        runner.update_container(self.candidate(), dry_run=False)
        guard.assert_called_once_with("wud-acquire")
        api.assert_not_called()

    @mock.patch.object(runner, "wait_for_service_check")
    @mock.patch.object(runner, "wait_for_healthy_replacement")
    @mock.patch.object(runner, "api_request")
    @mock.patch.object(runner, "docker_inspect")
    @mock.patch.object(runner, "associated_with_trigger", return_value=True)
    @mock.patch.object(runner, "storyteller_guard", side_effect=[True, True])
    def test_guard_releases_after_healthy_replacement(
        self,
        guard: mock.Mock,
        _associated: mock.Mock,
        inspect: mock.Mock,
        api: mock.Mock,
        replacement: mock.Mock,
        service_check: mock.Mock,
    ) -> None:
        inspect.return_value = {
            "Id": "old-container",
            "Image": "old-image",
            "Config": {"Image": "storyteller:latest"},
        }
        replacement.return_value = {
            "Id": "new-container",
            "Image": "new-image",
        }
        runner.update_container(self.candidate(), dry_run=False)
        self.assertEqual(
            guard.call_args_list,
            [mock.call("wud-acquire"), mock.call("wud-release")],
        )
        api.assert_called_once()
        replacement.assert_called_once()
        service_check.assert_called_once_with("apps", "storyteller")


if __name__ == "__main__":
    unittest.main()
