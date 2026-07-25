#!/usr/bin/env python3
"""Create or preserve Storyteller recovery values without displaying them."""

from __future__ import annotations

import argparse
import os
import secrets
import tempfile
from pathlib import Path


def parse_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value
    return values


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path("/root/.env"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = args.env_file
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    values = parse_values(lines)
    desired = {
        "STORYTELLER_SECRET_KEY": lambda: secrets.token_urlsafe(48),
        "STORYTELLER_ADMIN_EMAIL": lambda: "admin@rafael.media",
        "STORYTELLER_ADMIN_FULL_NAME": lambda: "Rafael Alani",
        "STORYTELLER_ADMIN_USERNAME": lambda: "rafael",
        "STORYTELLER_ADMIN_PASSWORD": lambda: secrets.token_urlsafe(32),
    }
    missing = [name for name in desired if not values.get(name)]
    if args.check:
        if missing:
            raise SystemExit(
                "Storyteller recovery environment is missing: "
                + ", ".join(missing)
            )
        if len(values["STORYTELLER_SECRET_KEY"]) < 32:
            raise SystemExit("STORYTELLER_SECRET_KEY is shorter than 32 characters")
        if len(values["STORYTELLER_ADMIN_PASSWORD"]) < 20:
            raise SystemExit("STORYTELLER_ADMIN_PASSWORD is shorter than 20 characters")
        print("Storyteller recovery environment check passed")
        return 0
    if missing:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("# Storyteller recovery values (generated; do not commit).")
        for name in missing:
            lines.append(f"{name}={desired[name]()}")
        atomic_write(path, "\n".join(lines) + "\n")
    else:
        os.chmod(path, 0o600)
    print(
        "Storyteller recovery environment initialized; "
        f"created={len(missing)} preserved={len(desired) - len(missing)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
