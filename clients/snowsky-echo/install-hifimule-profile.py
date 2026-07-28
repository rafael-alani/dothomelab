#!/usr/bin/env python3
"""Safely merge the repository SNOWSKY ECHO profile into HifiMule."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILE = SCRIPT_DIR / "hifimule-profile.json"
DEFAULT_PROFILES_FILE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "HifiMule"
    / "device-profiles.json"
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def validate_profile(value: Any, source: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{source} must contain one JSON object")
    for key in ("id", "name", "description", "deviceProfile"):
        if key not in value:
            raise ValueError(f"{source} is missing required key {key!r}")
    if not isinstance(value["id"], str) or not value["id"].strip():
        raise ValueError(f"{source} has an invalid profile id")
    if not isinstance(value["deviceProfile"], dict):
        raise ValueError(f"{source} deviceProfile must be an object")
    return value


def validate_profiles_document(value: Any, target: Path) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("profiles"), list):
        raise ValueError(f"{target} must contain a top-level profiles array")
    for index, profile in enumerate(value["profiles"]):
        if not isinstance(profile, dict):
            raise ValueError(f"{target} profile at index {index} is not an object")
        if not isinstance(profile.get("id"), str) or not profile["id"]:
            raise ValueError(f"{target} profile at index {index} has no valid id")
    return value


def next_backup_path(target: Path) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    candidate = target.with_name(f"{target.name}.backup-{timestamp}")
    counter = 1
    while candidate.exists():
        candidate = target.with_name(
            f"{target.name}.backup-{timestamp}-{counter}"
        )
        counter += 1
    return candidate


def atomic_write_json(target: Path, value: Any, mode: int) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            os.chmod(temp_path, mode)
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
        temp_path = None
        try:
            directory_fd = os.open(target.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def install(profile_file: Path, profiles_file: Path) -> tuple[bool, Path | None]:
    if profiles_file.is_symlink():
        raise ValueError(f"refusing to replace symlink {profiles_file}")
    if not profiles_file.exists():
        raise ValueError(
            f"{profiles_file} does not exist; launch and quit HifiMule once first"
        )
    if not profiles_file.is_file():
        raise ValueError(f"{profiles_file} is not a regular file")

    profile = validate_profile(load_json(profile_file), profile_file)
    document = validate_profiles_document(load_json(profiles_file), profiles_file)
    matching_indexes = [
        index
        for index, existing in enumerate(document["profiles"])
        if existing["id"] == profile["id"]
    ]
    if len(matching_indexes) > 1:
        raise ValueError(
            f"{profiles_file} contains duplicate profile id {profile['id']!r}"
        )

    if matching_indexes:
        index = matching_indexes[0]
        if document["profiles"][index] == profile:
            return False, None
        document["profiles"][index] = profile
    else:
        document["profiles"].append(profile)

    mode = stat.S_IMODE(profiles_file.stat().st_mode)
    backup = next_backup_path(profiles_file)
    shutil.copy2(profiles_file, backup)
    atomic_write_json(profiles_file, document, mode)
    return True, backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge the repository SNOWSKY ECHO profile into HifiMule's "
            "device-profiles.json with a timestamped backup and atomic replace."
        )
    )
    parser.add_argument(
        "--profile-file",
        type=Path,
        default=DEFAULT_PROFILE,
        help=f"profile object to install (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "--profiles-file",
        type=Path,
        default=DEFAULT_PROFILES_FILE,
        help=f"HifiMule profiles file (default: {DEFAULT_PROFILES_FILE})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        changed, backup = install(
            args.profile_file.expanduser(),
            args.profiles_file.expanduser(),
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    if not changed:
        print("SNOWSKY ECHO profile is already current; no files changed")
        return 0
    print("installed SNOWSKY ECHO profile")
    print(f"backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
