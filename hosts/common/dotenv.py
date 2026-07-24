#!/usr/bin/env python3
"""Parse the shell-independent subset of Docker Compose env files we use."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def decode_double_quoted(value: str, line_number: int) -> str:
    if len(value) < 2 or not value.endswith('"'):
        raise ValueError(f"line {line_number}: unterminated double-quoted value")
    inner = value[1:-1]
    replacements = {
        "\\": "\\",
        '"': '"',
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    result: list[str] = []
    index = 0
    while index < len(inner):
        if inner[index] != "\\":
            result.append(inner[index])
            index += 1
            continue
        index += 1
        if index >= len(inner):
            raise ValueError(f"line {line_number}: trailing backslash")
        escaped = inner[index]
        result.append(replacements.get(escaped, f"\\{escaped}"))
        index += 1
    return "".join(result)


def parse(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"line {line_number}: expected KEY=VALUE")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not KEY.fullmatch(key):
            raise ValueError(f"line {line_number}: invalid variable name {key!r}")

        value = raw_value.strip()
        if value.startswith("'"):
            if len(value) < 2 or not value.endswith("'"):
                raise ValueError(
                    f"line {line_number}: unterminated single-quoted value"
                )
            value = value[1:-1]
        elif value.startswith('"'):
            value = decode_double_quoted(value, line_number)
        else:
            # Compose treats a whitespace-prefixed # as an inline comment,
            # while an embedded # remains part of an unquoted value.
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        entries.append((key, value))
    return entries


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--check", action="store_true")
    argument_parser.add_argument("path", type=Path)
    args = argument_parser.parse_args()

    try:
        entries = parse(args.path)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"{args.path}: {error}", file=sys.stderr)
        return 1

    if not args.check:
        output = sys.stdout.buffer
        for key, value in entries:
            output.write(key.encode("utf-8"))
            output.write(b"\0")
            output.write(value.encode("utf-8"))
            output.write(b"\0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
