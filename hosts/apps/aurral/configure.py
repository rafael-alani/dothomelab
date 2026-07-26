#!/usr/bin/env python3
"""Idempotently configure Aurral without displaying integration secrets."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://192.168.0.112:3001"


def request(
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    token: str | None = None,
) -> object:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Aurral {method} {path} returned HTTP {error.code}: {detail}"
        ) from error
    return json.loads(body) if body else {}


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def main() -> int:
    username = required("AURRAL_ADMIN_USERNAME")
    password = required("AURRAL_ADMIN_PASSWORD")
    email = required("AURRAL_ADMIN_EMAIL")
    lidarr_key = required("LIDARR_API_KEY")
    navidrome_user = required("NAVIDROME_AURRAL_USERNAME")
    navidrome_password = required("NAVIDROME_AURRAL_PASSWORD")

    bootstrap = request("/api/health/bootstrap")
    if bootstrap.get("onboardingRequired") is True:
        query = urllib.parse.urlencode(
            {
                "url": "http://192.168.0.102:8686",
                "apiKey": lidarr_key,
            }
        )
        result = request(f"/api/onboarding/lidarr/test?{query}")
        if result.get("success") is not True:
            raise RuntimeError("Aurral rejected the Lidarr integration")
        result = request(
            "/api/onboarding/navidrome/test",
            method="POST",
            payload={
                "url": "http://192.168.0.112:4533",
                "username": navidrome_user,
                "password": navidrome_password,
            },
        )
        if result.get("success") is not True:
            raise RuntimeError("Aurral rejected the Navidrome integration")
        result = request(
            "/api/onboarding/complete",
            method="POST",
            payload={
                "authUser": username,
                "authPassword": password,
                "lidarr": {
                    "url": "http://192.168.0.102:8686",
                    "externalUrl": "https://lidarr.rafael.media",
                    "apiKey": lidarr_key,
                },
                "metadata": {
                    "baseUrl": "https://lidarrapi.brainzmash.cc",
                    "userAgentSuffix": email,
                    "enableNarrowFallbacks": True,
                },
                "navidrome": {
                    "url": "http://192.168.0.112:4533",
                    "username": navidrome_user,
                    "password": navidrome_password,
                },
            },
        )
        if result.get("success") is not True:
            raise RuntimeError("Aurral onboarding did not complete")

    login = request(
        "/api/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    token = str(login.get("token", ""))
    if not token:
        raise RuntimeError("Aurral administrator login returned no session")
    settings = request("/api/settings", token=token)
    integrations = settings.get("integrations") or {}
    expected = {
        "lidarr": ("url", "http://192.168.0.102:8686"),
        "navidrome": ("url", "http://192.168.0.112:4533"),
    }
    for group, (key, value) in expected.items():
        if (integrations.get(group) or {}).get(key) != value:
            raise RuntimeError(f"Aurral {group} integration drifted")
    if settings.get("rootFolderPath") != "/data/media/music":
        settings["rootFolderPath"] = "/data/media/music"
        request("/api/settings", method="POST", payload=settings, token=token)

    bootstrap = request("/api/health/bootstrap")
    if (
        bootstrap.get("onboardingRequired") is not False
        or bootstrap.get("lidarrConfigured") is not True
    ):
        raise RuntimeError("Aurral bootstrap state is incomplete")
    print("Aurral onboarding and Lidarr/Navidrome integrations verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
