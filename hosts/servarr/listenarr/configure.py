#!/usr/bin/env python3
"""Idempotently configure Listenarr for the existing Servarr acquisition stack."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from typing import Any

BASE_URL = "http://127.0.0.1:4545/api/v1"
PROWLARR_CONFIG = "/docker/prowlarr/config.xml"
PROFILE_NAME = "Audiobooks (M4B preferred)"


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


class Client:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        data = None
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{BASE_URL}{path}", data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(
                f"Listenarr {method} {path} failed with HTTP {error.code}: {detail}"
            ) from error
        return json.loads(body) if body else None


def wait_ready(client: Client) -> None:
    deadline = time.monotonic() + 180
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            bootstrap = client.request("GET", "/configuration/bootstrap")
            if bootstrap.get("authenticationRequired") is True:
                return
        except Exception as error:
            last_error = error
        time.sleep(3)
    raise RuntimeError(f"Listenarr did not become ready: {last_error}")


def desired_settings(current: dict[str, Any], admin_password: str) -> dict[str, Any]:
    desired = dict(current)
    desired.update(
        {
            "outputPath": "/audiobooks",
            "folderNamingPattern": "{Author}/{Title}",
            "fileNamingPattern": "{Author} - {Title}",
            "multiFileNamingPattern": "{Title}-{DiskNumber:00}-{ChapterNumber:00}",
            "enableMetadataProcessing": False,
            "enableCoverArtDownload": False,
            "maxConcurrentDownloads": 3,
            "pollingIntervalSeconds": 30,
            "allowedFileExtensions": [
                ".mp3",
                ".flac",
                ".m4a",
                ".m4b",
                ".ogg",
                ".opus",
            ],
            "downloadCompletionStabilitySeconds": 30,
            "missingSourceRetryInitialDelaySeconds": 30,
            "missingSourceMaxRetries": 5,
            "completedFileAction": "hardlink/copy",
            "extractArchives": True,
            "unmatchedScanConcurrency": 2,
            "showCompletedExternalDownloads": False,
            "historyRetentionDays": 365,
            "failedDownloadHandlingEnabled": True,
            "failedDownloadAutoSearch": False,
            "enableAmazonSearch": True,
            "enableAudibleSearch": True,
            "enableOpenLibrarySearch": True,
            "defaultSearchRegion": "us",
            "defaultSearchLanguage": "english",
            "adminUsername": "rafael",
            "adminPassword": admin_password,
        }
    )
    return desired


def quality_definitions() -> list[dict[str, Any]]:
    values = [
        ("FLAC", "FLAC", None, True),
        ("AAC 320kbps", "AAC", 320, False),
        ("AAC 256kbps", "AAC", 256, False),
        ("AAC 192kbps", "AAC", 192, False),
        ("AAC 128kbps", "AAC", 128, False),
        ("AAC 64kbps", "AAC", 64, False),
        ("MP3 320kbps", "MP3", 320, False),
        ("MP3 256kbps", "MP3", 256, False),
        ("MP3 VBR", "MP3", None, False),
        ("MP3 192kbps", "MP3", 192, False),
        ("MP3 128kbps", "MP3", 128, False),
        ("MP3 64kbps", "MP3", 64, False),
    ]
    return [
        {
            "quality": quality,
            "allowed": True,
            "priority": priority,
            "codec": codec,
            "bitrate": bitrate,
            "isLossless": lossless,
        }
        for priority, (quality, codec, bitrate, lossless) in enumerate(values)
    ]


def reconcile_root(client: Client) -> None:
    roots = client.request("GET", "/rootfolders")
    matches = [item for item in roots if item.get("path") == "/audiobooks"]
    payload = {
        "name": "Canonical Audiobooks",
        "path": "/audiobooks",
        "isDefault": True,
    }
    if matches:
        payload["id"] = matches[0]["id"]
        client.request("PUT", f"/rootfolders/{matches[0]['id']}", payload)
    else:
        client.request("POST", "/rootfolders", payload)


def reconcile_profile(client: Client) -> None:
    profiles = client.request("GET", "/qualityprofile")
    match = next((item for item in profiles if item.get("name") == PROFILE_NAME), None)
    payload: dict[str, Any] = {
        "name": PROFILE_NAME,
        "description": (
            "Unabridged English audiobooks; prefer M4B while accepting common "
            "lossy and lossless formats."
        ),
        "qualities": quality_definitions(),
        "cutoffQuality": "AAC 128kbps",
        "minimumSize": 0,
        "maximumSize": 0,
        "preferredFormats": ["m4b", "m4a", "mp3", "flac", "opus"],
        "preferredWords": ["unabridged", "retail", "m4b"],
        "mustNotContain": ["abridged", "summary", "sample"],
        "mustContain": [],
        "preferredLanguages": ["English"],
        "minimumSeeders": 1,
        "minimumScore": 0,
        "isDefault": True,
        "preferNewerReleases": False,
        "maximumAge": 0,
    }
    if match:
        payload["id"] = match["id"]
        client.request("PUT", f"/qualityprofile/{match['id']}", payload)
    else:
        client.request("POST", "/qualityprofile", payload)


def reconcile_clients(client: Client, nzb_user: str, nzb_password: str) -> None:
    desired = [
        {
            "id": "dothomelab-qbittorrent",
            "name": "Existing qBittorrent",
            "type": "qbittorrent",
            "host": "gluetun",
            "port": 8080,
            "username": "",
            "password": "",
            "downloadPath": "/data/torrents/completed/listenarr",
            "useSSL": False,
            "isEnabled": True,
            "removeCompletedDownloads": "none",
            "settings": {
                "category": "listenarr",
                "postImportCategory": "listenarr",
                "PollingIntervalSeconds": 30,
            },
        },
        {
            "id": "dothomelab-nzbget",
            "name": "Existing NZBGet",
            "type": "nzbget",
            "host": "gluetun",
            "port": 6789,
            "username": nzb_user,
            "password": nzb_password,
            "downloadPath": "/downloads/completed",
            "useSSL": False,
            "isEnabled": True,
            "removeCompletedDownloads": "remove_and_delete",
            "settings": {"category": "Books", "PollingIntervalSeconds": 30},
        },
    ]
    for payload in desired:
        result = client.request("POST", "/download-clients/test", payload)
        if not result.get("success"):
            raise RuntimeError(
                f"{payload['name']} connection failed: {result.get('message')}"
            )
        client.request("POST", "/download-clients", payload)


def reconcile_indexers(client: Client, prowlarr_key: str) -> None:
    client.request(
        "POST",
        "/indexers/prowlarr/import",
        {
            "url": "http://gluetun",
            "port": 9696,
            "clearPort": False,
            "apiKey": prowlarr_key,
            "tagFilter": "",
        },
    )
    indexers = client.request("GET", "/indexers")
    if not indexers:
        raise RuntimeError("Prowlarr imported no audiobook-related indexers")
    automatic = 0
    for indexer in indexers:
        category_ids = {
            value.strip() for value in (indexer.get("categories") or "").split(",")
        }
        audiobook_specific = "3030" in category_ids
        indexer.update(
            {
                "enableRss": audiobook_specific,
                "enableAutomaticSearch": audiobook_specific,
                "enableInteractiveSearch": True,
                "enableAnimeStandardSearch": False,
                "isEnabled": True,
            }
        )
        client.request("PUT", f"/indexers/{indexer['id']}", indexer)
        if audiobook_specific:
            automatic += 1
    if automatic < 1:
        raise RuntimeError("No category-3030 audiobook indexer is available")


def verify(client: Client) -> None:
    settings = client.request("GET", "/configuration/settings")
    expected = {
        "outputPath": "/audiobooks",
        "folderNamingPattern": "{Author}/{Title}",
        "fileNamingPattern": "{Author} - {Title}",
        "multiFileNamingPattern": "{Title}-{DiskNumber:00}-{ChapterNumber:00}",
        "enableMetadataProcessing": False,
        "enableCoverArtDownload": False,
        "completedFileAction": "hardlink/copy",
        "failedDownloadHandlingEnabled": True,
        "failedDownloadAutoSearch": False,
        "defaultSearchRegion": "us",
        "defaultSearchLanguage": "english",
    }
    for key, value in expected.items():
        if settings.get(key) != value:
            raise RuntimeError(f"Listenarr setting drifted: {key}")

    roots = client.request("GET", "/rootfolders")
    if (
        len(
            [
                item
                for item in roots
                if item.get("path") == "/audiobooks"
                and item.get("isDefault") is True
            ]
        )
        != 1
    ):
        raise RuntimeError("Listenarr canonical root folder is missing or ambiguous")

    profiles = client.request("GET", "/qualityprofile")
    if (
        len(
            [
                item
                for item in profiles
                if item.get("name") == PROFILE_NAME and item.get("isDefault") is True
            ]
        )
        != 1
    ):
        raise RuntimeError("Listenarr default audiobook quality profile drifted")

    clients = client.request("GET", "/download-clients")
    by_id = {
        item.get("id"): client.request("GET", f"/download-clients/{item['id']}")
        for item in clients
    }
    expected_clients = {
        "dothomelab-qbittorrent": (
            "qbittorrent",
            "/data/torrents/completed/listenarr",
            "none",
        ),
        "dothomelab-nzbget": ("nzbget", "/downloads/completed", "remove_and_delete"),
    }
    for identifier, expected_client in expected_clients.items():
        item = by_id.get(identifier)
        actual = (
            item.get("type") if item else None,
            item.get("downloadPath") if item else None,
            item.get("removeCompletedDownloads") if item else None,
        )
        if actual != expected_client:
            raise RuntimeError(f"Listenarr download client drifted: {identifier}")

    indexers = client.request("GET", "/indexers")
    automatic = [
        item
        for item in indexers
        if "3030" in (item.get("categories") or "").split(",")
        and item.get("enableAutomaticSearch") is True
        and item.get("enableInteractiveSearch") is True
    ]
    if not automatic:
        raise RuntimeError("Listenarr has no automatic category-3030 indexer")
    noisy_automatic = [
        item
        for item in indexers
        if "3030" not in (item.get("categories") or "").split(",")
        and item.get("enableAutomaticSearch") is True
    ]
    if noisy_automatic:
        raise RuntimeError("Generic book indexers are enabled for automatic search")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    api_key = required("LISTENARR_API_KEY")
    admin_password = required("LISTENARR_ADMIN_PASSWORD")
    nzb_user = required("NZBGET_USER")
    nzb_password = required("NZBGET_PASS")
    prowlarr_key = (
        ElementTree.parse(PROWLARR_CONFIG).getroot().findtext("ApiKey", "").strip()
    )
    if not prowlarr_key:
        raise RuntimeError("Prowlarr API key is missing")

    client = Client(api_key)
    wait_ready(client)
    if not args.check:
        settings = client.request("GET", "/configuration/settings")
        client.request(
            "POST",
            "/configuration/settings",
            desired_settings(settings, admin_password),
        )
        reconcile_root(client)
        reconcile_profile(client)
        reconcile_clients(client, nzb_user, nzb_password)
        reconcile_indexers(client, prowlarr_key)

    verify(client)
    print(
        "Listenarr authenticated settings, canonical root, clients, quality "
        "profile, and audiobook indexers verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
