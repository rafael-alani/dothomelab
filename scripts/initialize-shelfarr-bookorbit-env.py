#!/usr/bin/env python3
"""Create missing Shelfarr and BookOrbit recovery secrets without displaying them."""

from __future__ import annotations

import argparse
import os
import secrets
import string
import tempfile
from pathlib import Path

GENERATORS = {
    "SHELFARR_SECRET_KEY_BASE": lambda: secrets.token_hex(64),
    "SHELFARR_ADMIN_PASSWORD": lambda: strong_password(40),
    "SHELFARR_API_TOKEN": lambda: f"shf_{secrets.token_urlsafe(32)}",
    "BOOKORBIT_DB_PASSWORD": lambda: secrets.token_hex(32),
    "BOOKORBIT_JWT_SECRET": lambda: secrets.token_hex(32),
    "BOOKORBIT_SETUP_BOOTSTRAP_TOKEN": lambda: secrets.token_hex(32),
    "BOOKORBIT_ADMIN_PASSWORD": lambda: strong_password(40),
    "BOOKORBIT_OPDS_PASSWORD": lambda: strong_password(40),
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
        key = key.strip()
        if key:
            values[key] = value
    return values


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
        text=True,
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
    args = parser.parse_args()

    path = args.env_file
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    existing = parse_values(lines)
    generated = {
        key: generator()
        for key, generator in GENERATORS.items()
        if not existing.get(key)
    }
    additions = [
        f"{key}={value}" for key, value in generated.items() if key not in existing
    ]
    if generated:
        lines = [
            f"{key}={generated[key]}"
            if (
                "=" in line
                and not line.lstrip().startswith("#")
                and (key := line.split("=", 1)[0].strip()) in generated
            )
            else line
            for line in lines
        ]

    if generated:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(
            [
                "# Shelfarr and BookOrbit recovery secrets (generated; do not commit).",
                *additions,
            ]
        )
        write_atomic(path, "\n".join(lines) + "\n")
    else:
        os.chmod(path, 0o600)

    print(
        "Shelfarr/BookOrbit recovery environment initialized; "
        f"created={len(generated)} preserved={len(GENERATORS) - len(generated)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
