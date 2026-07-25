#!/usr/bin/env python3
"""Create missing Paperless-local values in /root/.env without printing them."""

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
    parser.add_argument("--admin-user", default="rafael")
    parser.add_argument("--admin-mail", default="rafael@localhost")
    parser.add_argument("--service-user", default="paperless-gpt")
    args = parser.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("run on the Proxmox host as root")
    if not ENV_PATH.is_file():
        raise SystemExit("/root/.env is missing")

    current = load_dotenv()
    desired = {
        "PAPERLESS_DB_PASSWORD": current.get("PAPERLESS_DB_PASSWORD")
        or secrets.token_urlsafe(32),
        "PAPERLESS_SECRET_KEY": current.get("PAPERLESS_SECRET_KEY")
        or secrets.token_hex(32),
        "PAPERLESS_ADMIN_USER": current.get("PAPERLESS_ADMIN_USER")
        or args.admin_user,
        "PAPERLESS_ADMIN_MAIL": current.get("PAPERLESS_ADMIN_MAIL")
        or args.admin_mail,
        "PAPERLESS_ADMIN_PASSWORD": current.get("PAPERLESS_ADMIN_PASSWORD")
        or secrets.token_urlsafe(32),
        "PAPERLESS_GPT_SERVICE_USER": current.get("PAPERLESS_GPT_SERVICE_USER")
        or args.service_user,
        "PAPERLESS_GPT_API_TOKEN": current.get("PAPERLESS_GPT_API_TOKEN")
        or secrets.token_hex(20),
        "PAPERLESS_GPT_LLM_MODEL": current.get("PAPERLESS_GPT_LLM_MODEL")
        or "gpt-4o-mini",
        "PAPERLESS_GPT_VISION_MODEL": current.get("PAPERLESS_GPT_VISION_MODEL")
        or "gpt-4o-mini",
        "PAPERLESS_GPT_LLM_LANGUAGE": current.get("PAPERLESS_GPT_LLM_LANGUAGE")
        or "English",
    }
    if not re.fullmatch(r"[0-9a-fA-F]{64}", desired["PAPERLESS_SECRET_KEY"]):
        raise SystemExit("existing PAPERLESS_SECRET_KEY is not 64 hexadecimal characters")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", desired["PAPERLESS_GPT_API_TOKEN"]):
        raise SystemExit(
            "existing PAPERLESS_GPT_API_TOKEN is not 40 hexadecimal characters"
        )
    if desired["PAPERLESS_ADMIN_USER"] == desired["PAPERLESS_GPT_SERVICE_USER"]:
        raise SystemExit(
            "PAPERLESS_GPT_SERVICE_USER must differ from PAPERLESS_ADMIN_USER"
        )

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
        output.extend(["", "# Paperless-ngx and Paperless-GPT"])
        output.extend(f"{key}={encode(desired[key])}" for key in added)

    temporary = ENV_PATH.with_name(f".{ENV_PATH.name}.paperless.tmp")
    temporary.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, ENV_PATH)

    openai_state = (
        "present" if current.get("PAPERLESS_GPT_OPENAI_API_KEY") else "missing"
    )
    print(
        "Paperless local environment ready; "
        f"added {len(added)} missing variables; OpenAI key {openai_state}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
