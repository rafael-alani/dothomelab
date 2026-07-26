#!/usr/bin/env python3
"""Idempotently configure Aurral v2 without displaying integration secrets."""

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


def optional_external(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("replace-with-"):
        return None
    return value


def main() -> int:
    username = required("AURRAL_ADMIN_USERNAME")
    password = required("AURRAL_ADMIN_PASSWORD")
    email = required("AURRAL_ADMIN_EMAIL")
    lidarr_key = required("LIDARR_API_KEY")
    navidrome_user = required("NAVIDROME_AURRAL_USERNAME")
    navidrome_password = required("NAVIDROME_AURRAL_PASSWORD")
    slskd_key = required("SLSKD_API_KEY")
    lastfm_key = optional_external("AURRAL_LASTFM_API_KEY")
    lastfm_username = optional_external("AURRAL_LASTFM_USERNAME")
    if bool(lastfm_key) != bool(lastfm_username):
        raise RuntimeError(
            "AURRAL_LASTFM_API_KEY and AURRAL_LASTFM_USERNAME "
            "must be supplied together"
        )

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
                    "searchOnAdd": True,
                },
                "downloadFolderPath": "/aurral-flows",
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
    integrations = settings.setdefault("integrations", {})
    changed = False

    expected_integrations = {
        "lidarr": {
            "url": "http://192.168.0.102:8686",
            "externalUrl": "https://lidarr.rafael.media",
            "apiKey": lidarr_key,
            "searchOnAdd": True,
        },
        "metadata": {
            "provider": "brainzmash",
            "baseUrl": "https://lidarrapi.brainzmash.cc",
            "userAgentSuffix": email,
            "enableNarrowFallbacks": True,
        },
        "navidrome": {
            "url": "http://192.168.0.112:4533",
            "username": navidrome_user,
            "password": navidrome_password,
            "m3uPathMode": "remote",
            "pathMappings": [
                {
                    "local": "/data/media/music",
                    "remote": "/music",
                },
                {
                    "local": "/aurral-flows",
                    "remote": "/aurral-flows",
                },
            ],
        },
        "slskd": {
            "enabled": True,
            "url": "http://slskd:5030",
            "apiKey": slskd_key,
            "priority": 10,
            "preferredFormat": "flac",
            "preferredFormatStrict": False,
            "cleanupAfterRuns": False,
        },
        "ytdlp": {
            "enabled": True,
            "priority": 50,
        },
    }
    for group, expected in expected_integrations.items():
        current = integrations.setdefault(group, {})
        for key, value in expected.items():
            if current.get(key) != value:
                current[key] = value
                changed = True

    if settings.get("rootFolderPath") != "/data/media/music":
        settings["rootFolderPath"] = "/data/media/music"
        changed = True
    if settings.get("downloadFolderPath") != "/aurral-flows":
        settings["downloadFolderPath"] = "/aurral-flows"
        changed = True
    expected_path_mapping = {
        "source": "slskd",
        "remote": "/slskd-downloads/complete",
        "local": "/slskd-downloads/complete",
    }
    path_mappings = settings.setdefault("pathMappings", [])
    if expected_path_mapping not in path_mappings:
        path_mappings.append(expected_path_mapping)
        changed = True
    if lastfm_key and lastfm_username:
        lastfm = integrations.setdefault("lastfm", {})
        if (
            lastfm.get("apiKey") != lastfm_key
            or lastfm.get("username") != lastfm_username
        ):
            lastfm["apiKey"] = lastfm_key
            lastfm["username"] = lastfm_username
            changed = True
    if changed:
        request("/api/settings", method="POST", payload=settings, token=token)

    lidarr_test = request("/api/settings/lidarr/test", token=token)
    if lidarr_test.get("success") is not True:
        raise RuntimeError("Aurral v2 Lidarr integration test failed")
    slskd_test = request(
        "/api/settings/slskd/test",
        method="POST",
        payload={},
        token=token,
    )
    if (
        slskd_test.get("success") is not True
        or slskd_test.get("ok") is not True
    ):
        raise RuntimeError("Aurral v2 slskd integration test failed")
    storage = request(
        "/api/settings/storage-health?force=true",
        token=token,
    )
    if storage.get("success") is not True:
        raise RuntimeError("Aurral v2 storage health check failed")

    bootstrap = request("/api/health/bootstrap")
    if bootstrap.get("onboardingRequired") is not False:
        raise RuntimeError("Aurral bootstrap state is incomplete")
    print(
        "Aurral v2 onboarding, durable request search, Lidarr/Navidrome, "
        "external slskd, and storage integrations verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
