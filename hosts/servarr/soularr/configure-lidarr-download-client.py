#!/usr/bin/env python3
"""Keep Lidarr's qBittorrent endpoint on stable Compose DNS."""

from __future__ import annotations

import copy
import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8686/api/v1"
EXPECTED_HOST = "gluetun"


def request(path: str, api_key: str, method: str = "GET", payload: object = None):
    data = None
    headers = {"X-Api-Key": api_key}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def host_field(client: dict) -> dict:
    for field in client.get("fields", []):
        if field.get("name") == "host":
            return field
    raise RuntimeError("qBittorrent client has no host field")


def main() -> int:
    api_key = os.environ.get("LIDARR_API_KEY", "")
    if len(api_key) < 16:
        raise RuntimeError("LIDARR_API_KEY is missing")

    clients = request("/downloadclient", api_key)
    matches = [
        client
        for client in clients
        if client.get("implementation", "").lower() == "qbittorrent"
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one qBittorrent client, found {len(matches)}"
        )

    current = matches[0]
    original = copy.deepcopy(current)
    current_host = host_field(current).get("value")
    if current_host == EXPECTED_HOST:
        request("/downloadclient/test", api_key, "POST", current)
        print("Lidarr qBittorrent client uses stable Compose DNS and passes its test")
        return 0

    host_field(current)["value"] = EXPECTED_HOST
    updated = request(
        f"/downloadclient/{current['id']}", api_key, "PUT", current
    )
    try:
        request("/downloadclient/test", api_key, "POST", updated)
    except Exception:
        request(
            f"/downloadclient/{original['id']}", api_key, "PUT", original
        )
        raise RuntimeError(
            "new qBittorrent endpoint failed its Lidarr test; original restored"
        )

    print("Lidarr qBittorrent client reconciled to stable Compose DNS and tested")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
