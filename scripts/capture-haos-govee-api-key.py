#!/usr/bin/env python3
"""Capture an existing HAOS Govee Platform API key without printing it."""

from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ADDON_SLUG = "b9845f46_govee2mqtt"
KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
ENV_PATTERN = re.compile(r"^[ \t]*GOVEE_API_KEY=(.*)$", re.MULTILINE)


def read_live_key(vmid: int) -> str:
    completed = subprocess.run(
        [
            "qm",
            "guest",
            "exec",
            str(vmid),
            "--",
            "ha",
            "apps",
            "info",
            ADDON_SLUG,
            "--raw-json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    outer = json.loads(completed.stdout)
    if outer.get("exitcode", 1) != 0:
        raise RuntimeError("HAOS failed to return Govee2MQTT app information")
    inner = json.loads(outer.get("out-data", ""))
    key = inner.get("data", {}).get("options", {}).get("govee_api_key")
    if not isinstance(key, str) or KEY_PATTERN.fullmatch(key) is None:
        raise RuntimeError("The live Govee Platform API key is missing or malformed")
    return key


def normalized_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def atomic_write(path: Path, text: str, owner: tuple[int, int]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        os.fchown(descriptor, *owner)
        with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
            destination.write(text)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy the configured HAOS Govee API key into a protected dotenv file."
    )
    parser.add_argument("--env-file", type=Path, default=Path("/root/.env"))
    parser.add_argument("--vmid", type=int, default=104)
    args = parser.parse_args()

    if os.geteuid() != 0:
        parser.error("run this capture as root on Proxmox")
    if not args.env_file.is_file():
        parser.error(f"environment file does not exist: {args.env_file}")

    key = read_live_key(args.vmid)
    current_text = args.env_file.read_text(encoding="utf-8")
    matches = list(ENV_PATTERN.finditer(current_text))
    if len(matches) > 1:
        raise RuntimeError("Refusing to modify duplicate GOVEE_API_KEY entries")
    if matches:
        if normalized_env_value(matches[0].group(1)) != key:
            raise RuntimeError(
                "Refusing to replace a different GOVEE_API_KEY in the recovery input"
            )
        os.chmod(args.env_file, 0o600)
        print("GOVEE_API_KEY already matches the live HAOS configuration.")
        return 0

    stat_result = args.env_file.stat()
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    rollback = args.env_file.with_name(f"{args.env_file.name}.pre-govee-{stamp}")
    rollback_descriptor = os.open(
        rollback,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    os.fchown(rollback_descriptor, stat_result.st_uid, stat_result.st_gid)
    with (
        args.env_file.open("rb") as source,
        os.fdopen(rollback_descriptor, "wb") as destination,
    ):
        shutil.copyfileobj(source, destination)
        destination.flush()
        os.fsync(destination.fileno())

    separator = "" if not current_text or current_text.endswith("\n") else "\n"
    addition = (
        "\n# Govee2MQTT uses the official Platform API for dynamic H60A1 scenes.\n"
        f"GOVEE_API_KEY={key}\n"
    )
    atomic_write(
        args.env_file,
        current_text + separator + addition,
        (stat_result.st_uid, stat_result.st_gid),
    )
    print(
        "Captured GOVEE_API_KEY into the protected recovery input; "
        f"rollback retained at {rollback}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
