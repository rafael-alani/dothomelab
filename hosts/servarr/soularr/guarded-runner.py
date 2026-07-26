#!/usr/bin/env python3
"""Run Soularr's UI and scheduler with an observable per-cycle file lock."""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import sys
import time

LOCK = "/data/.dothomelab-job.lock"
INTERVAL = int(os.environ.get("SCRIPT_INTERVAL", "300"))
ENABLED = os.environ.get("SOULARR_SCHEDULER_ENABLED", "false").lower() == "true"


def stop(process: subprocess.Popen[bytes] | None) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    ui: subprocess.Popen[bytes] | None = None
    if os.environ.get("WEBUI_ENABLED", "true").lower() == "true":
        ui = subprocess.Popen(
            [sys.executable, "-u", "/app/webui/webui.py"],
            start_new_session=True,
        )

    def terminate(_signum: int, _frame: object) -> None:
        stop(ui)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)

    while True:
        if ENABLED:
            with open(LOCK, "a+", encoding="utf-8") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                subprocess.run(
                    [sys.executable, "-u", "/app/soularr.py"],
                    check=False,
                )
        else:
            print(
                "Soularr automatic scheduler is paused; "
                "run an explicitly selected acceptance cycle or set "
                "SOULARR_SCHEDULER_ENABLED=true after Lidarr monitoring is curated.",
                flush=True,
            )
        time.sleep(INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
