#!/usr/bin/env python3
"""Create missing Grimmory recovery values without displaying secrets."""

from __future__ import annotations

import argparse
import os
import secrets
import string
import tempfile
from pathlib import Path

GENERATORS = {
    "GRIMMORY_DB_PASSWORD": lambda: secrets.token_hex(32),
    "GRIMMORY_DB_ROOT_PASSWORD": lambda: secrets.token_hex(32),
    "GRIMMORY_ADMIN_PASSWORD": lambda: strong_password(40),
}

DEFAULTS = {
    "GRIMMORY_ADMIN_USERNAME": "rafael",
    "GRIMMORY_ADMIN_EMAIL": "rafael@rafael.media",
    "GRIMMORY_ADMIN_NAME": "Rafael",
}


def strong_password(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in value)
            and any(char.isupper() for char in value)
            and any(char.isdigit() for char in value)
        ):
            return value


def parse_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip():
            values[key.strip()] = value
    return values


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path("/root/.env"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    path = args.env_file
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    existing = parse_values(lines)
    missing = [
        key for key in (*GENERATORS, *DEFAULTS) if not existing.get(key)
    ]
    if args.check:
        if missing:
            raise SystemExit(
                "Missing Grimmory recovery values: " + ", ".join(sorted(missing))
            )
        print("Grimmory recovery environment is complete")
        return 0

    replacements = {
        key: generator()
        for key, generator in GENERATORS.items()
        if not existing.get(key)
    } | {
        key: value for key, value in DEFAULTS.items() if not existing.get(key)
    }
    additions = [
        f"{key}={value}" for key, value in replacements.items() if key not in existing
    ]
    if replacements:
        lines = [
            f"{key}={replacements[key]}"
            if (
                "=" in line
                and not line.lstrip().startswith("#")
                and (key := line.split("=", 1)[0].strip()) in replacements
            )
            else line
            for line in lines
        ]
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(
            [
                "# Grimmory recovery values (generated; do not commit).",
                *additions,
            ]
        )
        write_atomic(path, "\n".join(lines) + "\n")
    else:
        os.chmod(path, 0o600)

    print(
        "Grimmory recovery environment initialized; "
        f"values_created={len(replacements)} "
        f"values_preserved={len(GENERATORS) + len(DEFAULTS) - len(replacements)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
