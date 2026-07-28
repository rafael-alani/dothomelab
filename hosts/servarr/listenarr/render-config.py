#!/usr/bin/env python3
"""Render Listenarr's authenticated startup configuration before first boot."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("/docker/listenarr/config.json")
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    api_key = required("LISTENARR_API_KEY")
    if len(api_key) != 64:
        raise RuntimeError("LISTENARR_API_KEY must contain exactly 64 characters")

    desired = {
        "LogLevel": "Information",
        "EnableSsl": False,
        "Port": 4545,
        "UrlBase": "",
        "BindAddress": "*",
        "ApiKey": api_key,
        "UpdateMechanism": "Docker",
        "LaunchBrowser": False,
        "Branch": "canary",
        "InstanceName": "Listenarr",
        "AnalyticsEnabled": False,
        "ApiVersion": "1",
        "AuthenticationRequired": "true",
    }

    current: dict[str, object] = {}
    if args.output.is_file():
        current = json.loads(args.output.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            raise RuntimeError("Listenarr config.json must contain an object")

    if args.check:
        for key, value in desired.items():
            if current.get(key) != value:
                raise RuntimeError(f"Listenarr startup setting drifted: {key}")
        mode = args.output.stat().st_mode & 0o777
        if mode != 0o600:
            raise RuntimeError(f"Listenarr config mode is {mode:o}, expected 600")
        if os.geteuid() == 0:
            stat = args.output.stat()
            if (stat.st_uid, stat.st_gid) != (1000, 1000):
                raise RuntimeError(
                    "Listenarr config owner is "
                    f"{stat.st_uid}:{stat.st_gid}, expected 1000:1000"
                )
        print("Listenarr authenticated startup configuration check passed")
        return 0

    current.update(desired)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".config.", dir=args.output.parent, text=True
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(current, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if os.geteuid() == 0:
            os.chown(temporary, 1000, 1000)
        os.replace(temporary, args.output)
        os.chmod(args.output, 0o600)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass

    print("Listenarr authenticated startup configuration rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
