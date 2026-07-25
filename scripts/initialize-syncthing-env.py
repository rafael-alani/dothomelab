#!/usr/bin/env python3
"""Create missing Syncthing GUI credentials without printing their values."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import secrets
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = Path("/root/.env")


def load_dotenv() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location(
        "dothomelab_dotenv", REPO_ROOT / "hosts/common/dotenv.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the repository dotenv parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.parse(ENV_PATH))


def encode(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="rafael")
    args = parser.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("run on the Proxmox host as root")
    if not ENV_PATH.is_file():
        raise SystemExit("/root/.env is missing")

    current = load_dotenv()
    desired = {
        "SYNCTHING_GUI_USERNAME": current.get("SYNCTHING_GUI_USERNAME")
        or args.username,
        "SYNCTHING_GUI_PASSWORD": current.get("SYNCTHING_GUI_PASSWORD")
        or secrets.token_urlsafe(32),
    }
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", desired["SYNCTHING_GUI_USERNAME"]):
        raise SystemExit(
            "SYNCTHING_GUI_USERNAME must contain 1-64 letters, numbers, dot, "
            "underscore, or hyphen"
        )
    if len(desired["SYNCTHING_GUI_PASSWORD"]) < 32:
        raise SystemExit("SYNCTHING_GUI_PASSWORD must contain at least 32 characters")

    managed = set(desired)
    key_pattern = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    original_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    written: set[str] = set()
    for line in original_lines:
        match = key_pattern.match(line)
        key = match.group(1) if match else ""
        if key not in managed:
            output.append(line)
            continue
        if key not in written:
            output.append(f"{key}={encode(desired[key])}")
            written.add(key)

    added = [key for key in desired if key not in written]
    if added:
        output.extend(["", "# Private Syncthing GUI"])
        output.extend(f"{key}={encode(desired[key])}" for key in added)

    temporary = ENV_PATH.with_name(f".{ENV_PATH.name}.syncthing.tmp")
    temporary.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, ENV_PATH)
    print(f"Syncthing GUI environment ready; added {len(added)} missing variables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
