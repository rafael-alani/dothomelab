#!/usr/bin/env python3
"""Create or verify Infra's first n8n owner without exposing its password."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("N8N_INTERNAL_URL", "http://192.168.0.110:5678")


def request(path: str, payload: dict[str, object] | None = None) -> object:
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method="GET" if body is None else "POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        # Authentication responses may echo private account information.
        raise RuntimeError(f"{path} returned HTTP {error.code}") from None
    return json.loads(raw) if raw else {}


def setup_pending(settings: object) -> bool:
    if isinstance(settings, dict):
        if settings.get("showSetupOnFirstLoad") is True:
            return True
        return any(setup_pending(value) for value in settings.values())
    if isinstance(settings, list):
        return any(setup_pending(value) for value in settings)
    return False


def verify_login(email: str, password: str) -> None:
    request('/rest/login', {'emailOrLdapLoginId': email, 'password': password})


def verify_retained_owner(database: Path) -> None:
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        owners = connection.execute(
            'SELECT email,password,disabled FROM user WHERE roleSlug = ?',
            ('global:owner',),
        ).fetchall()
    if len(owners) != 1 or not owners[0][0] or not owners[0][1] or owners[0][2]:
        raise RuntimeError('n8n requires one enabled retained owner with local authentication state')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument('--verify-login', action='store_true',
                        help='Additionally test the bootstrap credentials against the current account')
    args = parser.parse_args()

    required = (
        "N8N_ADMIN_EMAIL",
        "N8N_ADMIN_FIRST_NAME",
        "N8N_ADMIN_LAST_NAME",
        "N8N_ADMIN_PASSWORD",
    )
    deadline = time.monotonic() + 180
    while True:
        try:
            settings = request("/rest/settings")
            break
        except (RuntimeError, urllib.error.URLError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(5)
    pending = setup_pending(settings)
    if args.verify and pending:
        raise SystemExit("n8n still requires first-owner setup")
    if pending or args.verify_login:
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise SystemExit(f"missing required n8n owner variables: {', '.join(missing)}")
        email = os.environ['N8N_ADMIN_EMAIL']
        password = os.environ['N8N_ADMIN_PASSWORD']
    if pending:
        request(
            "/rest/owner/setup",
            {
                "email": email,
                "firstName": os.environ["N8N_ADMIN_FIRST_NAME"],
                "lastName": os.environ["N8N_ADMIN_LAST_NAME"],
                "password": password,
            },
        )
        verify_login(email, password)
        print('n8n first-owner setup and authentication verified')
    else:
        verify_retained_owner(Path(os.environ.get(
            'N8N_DATABASE_PATH', '/srv/appdata/docker/n8n/database.sqlite')).resolve())
        if args.verify_login:
            verify_login(email, password)
            print('n8n current owner authentication verified')
        else:
            print('n8n retained owner state verified; current login credentials were not tested')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
