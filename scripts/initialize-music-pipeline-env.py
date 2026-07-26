#!/usr/bin/env python3
"""Create or preserve music-pipeline recovery values without displaying them."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import string
import tempfile
from pathlib import Path


def strong_password(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(character.islower() for character in value)
            and any(character.isupper() for character in value)
            and any(character.isdigit() for character in value)
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


def lidarr_api_key(config: Path) -> str:
    if not config.is_file():
        raise RuntimeError(f"Lidarr config is missing: {config}")
    match = re.search(
        r"<ApiKey>([^<]+)</ApiKey>",
        config.read_text(encoding="utf-8"),
    )
    if not match or len(match.group(1).strip()) < 16:
        raise RuntimeError("Lidarr API key is missing from its recovered config")
    return match.group(1).strip()


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
    parser.add_argument(
        "--lidarr-config",
        type=Path,
        default=Path("/srv/appdata/docker/lidarr/config.xml"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    path = args.env_file
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    values = parse_values(lines)
    desired = {
        "LIDARR_API_KEY": lambda: lidarr_api_key(args.lidarr_config),
        "AURRAL_ADMIN_EMAIL": lambda: values.get(
            "PINEPODS_ADMIN_EMAIL", "admin@rafael.media"
        ),
        "AURRAL_ADMIN_USERNAME": lambda: "rafael",
        "AURRAL_ADMIN_PASSWORD": lambda: strong_password(40),
        "NAVIDROME_ADMIN_USERNAME": lambda: "rafael",
        "NAVIDROME_ADMIN_PASSWORD": lambda: strong_password(40),
        "NAVIDROME_AURRAL_USERNAME": lambda: "aurral-integration",
        "NAVIDROME_AURRAL_PASSWORD": lambda: strong_password(40),
    }
    missing = [name for name in desired if not values.get(name)]

    if args.check:
        if missing:
            raise SystemExit(
                "Music-pipeline recovery environment is missing: "
                + ", ".join(missing)
            )
        if len(values["LIDARR_API_KEY"]) < 16:
            raise SystemExit("LIDARR_API_KEY is shorter than 16 characters")
        for name in (
            "AURRAL_ADMIN_PASSWORD",
            "NAVIDROME_ADMIN_PASSWORD",
            "NAVIDROME_AURRAL_PASSWORD",
        ):
            if len(values[name]) < 20:
                raise SystemExit(f"{name} is shorter than 20 characters")
        print("Music-pipeline recovery environment check passed")
        return 0

    if missing:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("# Music-pipeline recovery values (generated; do not commit).")
        for name in missing:
            lines.append(f"{name}={desired[name]()}")
        atomic_write(path, "\n".join(lines) + "\n")
    else:
        os.chmod(path, 0o600)

    print(
        "Music-pipeline recovery environment initialized; "
        f"created={len(missing)} preserved={len(desired) - len(missing)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
