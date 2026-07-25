#!/usr/bin/env python3
"""Create or verify Infra's first n8n owner without exposing its password."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:5678"


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
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"{path} returned HTTP {error.code}: {detail[:300]}") from error
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
    payloads = (
        {"emailOrLdapLoginId": email, "password": password},
        {"email": email, "password": password},
    )
    last_error: Exception | None = None
    for payload in payloads:
        try:
            request("/rest/login", payload)
            return
        except RuntimeError as error:
            last_error = error
    raise RuntimeError("n8n owner login verification failed") from last_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    required = (
        "N8N_ADMIN_EMAIL",
        "N8N_ADMIN_FIRST_NAME",
        "N8N_ADMIN_LAST_NAME",
        "N8N_ADMIN_PASSWORD",
    )
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise SystemExit(f"missing required n8n owner variables: {', '.join(missing)}")

    email = os.environ["N8N_ADMIN_EMAIL"]
    password = os.environ["N8N_ADMIN_PASSWORD"]
    pending = setup_pending(request("/rest/settings"))
    if args.verify and pending:
        raise SystemExit("n8n still requires first-owner setup")
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
    print("n8n owner authentication verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
