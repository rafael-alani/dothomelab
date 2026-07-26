#!/usr/bin/env python3
"""Idempotently configure Navidrome users and libraries."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = "http://192.168.0.112:4533"


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def request(
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    token: str | None = None,
    accepted: tuple[int, ...] = (200,),
) -> tuple[int, object]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-ND-Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as error:
        if error.code in accepted:
            status = error.code
            body = error.read()
        else:
            detail = error.read().decode("utf-8", "replace")
            raise RuntimeError(
                f"Navidrome {method} {path} returned HTTP {error.code}: {detail}"
            ) from error
    if status not in accepted:
        raise RuntimeError(
            f"Navidrome {method} {path} returned unexpected HTTP {status}"
        )
    return status, json.loads(body) if body else {}


def login(username: str, password: str) -> dict[str, object]:
    _, payload = request(
        "/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    if not isinstance(payload, dict) or not payload.get("token"):
        raise RuntimeError("Navidrome login returned no token")
    return payload


def main() -> int:
    admin_user = required("NAVIDROME_ADMIN_USERNAME")
    admin_password = required("NAVIDROME_ADMIN_PASSWORD")
    integration_user = required("NAVIDROME_AURRAL_USERNAME")
    integration_password = required("NAVIDROME_AURRAL_PASSWORD")

    try:
        session = login(admin_user, admin_password)
    except RuntimeError:
        _, session = request(
            "/auth/createAdmin",
            method="POST",
            payload={"username": admin_user, "password": admin_password},
            accepted=(200, 403),
        )
        if not isinstance(session, dict) or not session.get("token"):
            session = login(admin_user, admin_password)
    token = str(session["token"])

    _, libraries_payload = request("/api/library", token=token)
    if not isinstance(libraries_payload, list):
        raise RuntimeError("Navidrome library response is not a list")
    libraries = {
        str(item.get("path")): item
        for item in libraries_payload
        if isinstance(item, dict)
    }
    if "/music" not in libraries:
        _, created = request(
            "/api/library",
            method="POST",
            payload={"name": "Music", "path": "/music"},
            token=token,
        )
        libraries["/music"] = created
    if "/aurral-flows" not in libraries:
        _, created = request(
            "/api/library",
            method="POST",
            payload={
                "name": "Aurral Weekly Flow",
                "path": "/aurral-flows",
            },
            token=token,
        )
        libraries["/aurral-flows"] = created

    _, users_payload = request("/api/user", token=token)
    if not isinstance(users_payload, list):
        raise RuntimeError("Navidrome user response is not a list")
    integration = next(
        (
            item
            for item in users_payload
            if isinstance(item, dict)
            and item.get("userName") == integration_user
        ),
        None,
    )
    if integration is None:
        _, integration = request(
            "/api/user",
            method="POST",
            payload={
                "userName": integration_user,
                "name": "Aurral integration",
                "email": "",
                "password": integration_password,
                "isAdmin": False,
            },
            token=token,
        )
    if not isinstance(integration, dict) or not integration.get("id"):
        raise RuntimeError("Navidrome Aurral integration user is invalid")

    library_ids = sorted(int(item["id"]) for item in libraries.values())
    request(
        f"/api/user/{integration['id']}/library",
        method="PUT",
        payload={"libraryIds": library_ids},
        token=token,
    )
    integration_session = login(integration_user, integration_password)
    if integration_session.get("isAdmin") is not False:
        raise RuntimeError("Aurral Navidrome account must remain non-admin")
    print("Navidrome administrator, libraries, and Aurral integration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
