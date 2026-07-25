#!/usr/bin/env python3
"""Add first-deployment n8n/Pulse secrets to /root/.env without printing them."""

from __future__ import annotations

import argparse
import os
import re
import secrets
from pathlib import Path

ENV_PATH = Path("/root/.env")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n8n-email", default="admin@rafael.media")
    parser.add_argument("--n8n-first-name", default="Rafael")
    parser.add_argument("--n8n-last-name", default="Alani")
    parser.add_argument("--pulse-user", default="rafael")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run on the Proxmox host as root")
    if not ENV_PATH.is_file():
        raise SystemExit("/root/.env is missing")

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    keys = {
        match.group(1)
        for line in lines
        if (match := re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line))
    }
    desired = {
        "N8N_ENCRYPTION_KEY": secrets.token_hex(32),
        "N8N_ADMIN_EMAIL": args.n8n_email,
        "N8N_ADMIN_FIRST_NAME": args.n8n_first_name,
        "N8N_ADMIN_LAST_NAME": args.n8n_last_name,
        "N8N_ADMIN_PASSWORD": secrets.token_urlsafe(32),
        "PULSE_AUTH_USER": args.pulse_user,
        "PULSE_AUTH_PASS": secrets.token_urlsafe(32),
    }
    added = [key for key in desired if key not in keys]
    if added:
        lines.extend(["", "# n8n and Pulse"])
        for key in added:
            value = desired[key].replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key}="{value}"')
        temporary = ENV_PATH.with_name(f".{ENV_PATH.name}.n8n-pulse.tmp")
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, ENV_PATH)
    print(f"n8n/Pulse environment ready; added {len(added)} missing variables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
