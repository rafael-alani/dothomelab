#!/usr/bin/env python3
"""Reconcile Cleanuparr through its supported HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


BASE_URL = os.environ.get(
    "CLEANUPARR_BASE_URL", "http://127.0.0.1:11011"
).rstrip("/")
QBITTORRENT_NAME = "CT102 qBittorrent"
STALL_RULES = {
    "dothomelab public stalled torrents": {
        "name": "dothomelab public stalled torrents",
        "enabled": True,
        "maxStrikes": 12,
        "privacyType": "Public",
        "minCompletionPercentage": 0,
        "maxCompletionPercentage": 100,
        "deletePrivateTorrentsFromClient": False,
        "changeCategory": False,
        "resetStrikesOnProgress": True,
        "minimumProgress": "64MB",
    },
    "dothomelab private stalled torrents": {
        "name": "dothomelab private stalled torrents",
        "enabled": True,
        "maxStrikes": 48,
        "privacyType": "Private",
        "minCompletionPercentage": 0,
        "maxCompletionPercentage": 100,
        "deletePrivateTorrentsFromClient": True,
        "changeCategory": False,
        "resetStrikesOnProgress": True,
        "minimumProgress": "64MB",
    },
}
ARRS = {
    "sonarr": (
        "CT102 Sonarr",
        "http://sonarr:8989",
        "http://192.168.0.102:8989",
        4.0,
        "SONARR_API_KEY",
    ),
    "radarr": (
        "CT102 Radarr",
        "http://radarr:7878",
        "http://192.168.0.102:7878",
        6.0,
        "RADARR_API_KEY",
    ),
    "lidarr": (
        "CT102 Lidarr",
        "http://lidarr:8686",
        "http://192.168.0.102:8686",
        3.0,
        "LIDARR_API_KEY",
    ),
    "readarr": (
        "CT102 Readarr",
        "http://readarr:8787",
        "http://192.168.0.102:8787",
        0.4,
        "READARR_API_KEY",
    ),
}


class Api:
    def __init__(self) -> None:
        self.token = ""

    def request(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
        allowed: tuple[int, ...] = (200,),
    ) -> Any:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated:
            if not self.token:
                raise RuntimeError("Cleanuparr API authentication is unavailable")
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            BASE_URL + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
                if response.status not in allowed:
                    raise RuntimeError(
                        f"Cleanuparr {method} {path} returned HTTP {response.status}"
                    )
        except urllib.error.HTTPError as error:
            if error.code in allowed:
                content = error.read()
            else:
                raise RuntimeError(
                    f"Cleanuparr {method} {path} returned HTTP {error.code}"
                ) from error
        if not content:
            return None
        return json.loads(content)


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def wait_for_health() -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL + "/health", timeout=5) as response:
                if response.status == 200 and response.read() == b"healthy":
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(2)
    raise RuntimeError("Cleanuparr did not become healthy")


def authenticate(api: Api) -> None:
    username = required("CLEANUPARR_ADMIN_USERNAME")
    password = required("CLEANUPARR_ADMIN_PASSWORD")
    status = api.request("/api/auth/status", authenticated=False)
    if not status.get("setupCompleted"):
        api.request(
            "/api/auth/setup/account",
            "POST",
            {"username": username, "password": password},
            authenticated=False,
            allowed=(201, 409),
        )
        api.request(
            "/api/auth/setup/complete",
            "POST",
            authenticated=False,
            allowed=(200, 409),
        )
    login = api.request(
        "/api/auth/login",
        "POST",
        {"username": username, "password": password},
        authenticated=False,
    )
    if login.get("requiresTwoFactor"):
        raise RuntimeError(
            "Cleanuparr 2FA is enabled; API reconciliation needs a non-2FA "
            "recovery administrator"
        )
    api.token = login.get("tokens", {}).get("accessToken", "")
    if not api.token:
        raise RuntimeError("Cleanuparr login did not return an access token")


def desired_general(current: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    return {
        "displaySupportBanner": False,
        "dryRun": dry_run,
        "httpMaxRetries": 2,
        "httpTimeout": 30,
        "httpCertificateValidation": "Enabled",
        "statusCheckEnabled": False,
        "encryptionKey": current["encryptionKey"],
        "ignoredDownloads": current.get("ignoredDownloads", []),
        "connectivityCheckEnabled": True,
        "connectivityCheckUrls": [
            "https://www.google.com/generate_204",
            "https://www.cloudflare.com/cdn-cgi/trace",
        ],
        "strikeInactivityWindowHours": 168,
        "historyRetentionDays": 365,
        "log": {
            "level": "Information",
            "rollingSizeMB": 10,
            "retainedFileCount": 5,
            "timeLimitHours": 24,
            "archiveEnabled": True,
            "archiveRetainedCount": 30,
            "archiveTimeLimitHours": 720,
        },
        "auth": {
            "disableAuthForLocalAddresses": False,
            "trustForwardedHeaders": False,
            "trustedNetworks": [],
        },
    }


def upsert_download_client(api: Api) -> None:
    desired = {
        "enabled": True,
        "name": QBITTORRENT_NAME,
        "typeName": "qBittorrent",
        "type": "Torrent",
        "host": "http://gluetun:8080",
        "username": "",
        "password": "",
        "urlBase": "",
        "externalUrl": "http://192.168.0.102:8080",
        "downloadDirectorySource": "",
        "downloadDirectoryTarget": "",
    }
    api.request(
        "/api/configuration/download_client/test",
        "POST",
        {
            "typeName": desired["typeName"],
            "type": desired["type"],
            "host": desired["host"],
            "username": "",
            "password": "",
            "urlBase": "",
        },
    )
    clients = api.request("/api/configuration/download_client").get("clients", [])
    matches = [item for item in clients if item.get("name") == QBITTORRENT_NAME]
    if len(matches) > 1:
        raise RuntimeError("Cleanuparr has duplicate repository-owned qBittorrent clients")
    if matches:
        api.request(
            f"/api/configuration/download_client/{matches[0]['id']}",
            "PUT",
            desired,
        )
    else:
        api.request(
            "/api/configuration/download_client",
            "POST",
            desired,
            allowed=(201,),
        )


def upsert_arrs(api: Api) -> None:
    for arr_type, (name, url, external_url, version, env_name) in ARRS.items():
        key = required(env_name)
        api.request(
            f"/api/configuration/{arr_type}/instances/test",
            "POST",
            {"url": url, "apiKey": key, "version": version},
        )
        config = api.request(f"/api/configuration/{arr_type}")
        matches = [
            item for item in config.get("instances", []) if item.get("name") == name
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"Cleanuparr has duplicate repository-owned {arr_type} instances"
            )
        desired = {
            "enabled": True,
            "name": name,
            "url": url,
            "apiKey": key,
            "version": version,
            "externalUrl": external_url,
        }
        if matches:
            api.request(
                f"/api/configuration/{arr_type}/instances/{matches[0]['id']}",
                "PUT",
                desired,
            )
        else:
            api.request(
                f"/api/configuration/{arr_type}/instances",
                "POST",
                desired,
                allowed=(201,),
            )
        api.request(
            f"/api/configuration/{arr_type}",
            "PUT",
            {"failedImportMaxStrikes": 0},
        )


def upsert_stall_rules(api: Api) -> None:
    current = api.request("/api/queue-rules/stall")
    for name, desired in STALL_RULES.items():
        matches = [item for item in current if item.get("name") == name]
        if len(matches) > 1:
            raise RuntimeError(f"Cleanuparr has duplicate stall rule: {name}")
        if matches:
            api.request(
                f"/api/queue-rules/stall/{matches[0]['id']}",
                "PUT",
                desired,
            )
        else:
            api.request(
                "/api/queue-rules/stall",
                "POST",
                desired,
                allowed=(201,),
            )


def configure_queue_and_seeker(api: Api) -> None:
    api.request(
        "/api/configuration/queue_cleaner",
        "PUT",
        {
            "enabled": True,
            "cronExpression": "0 0/30 * ? * * *",
            "useAdvancedScheduling": True,
            "failedImport": {
                "maxStrikes": 0,
                "ignorePrivate": True,
                "deletePrivate": False,
                "skipIfNotFoundInClient": True,
                "patterns": [],
                "patternMode": "Exclude",
                "changeCategory": False,
            },
            "downloadingMetadataMaxStrikes": 12,
            "processNoContentId": False,
            "ignoredDownloads": [],
        },
    )
    seeker = api.request("/api/configuration/seeker")
    instances = []
    for item in seeker.get("instances", []):
        instances.append(
            {
                "arrInstanceId": item["arrInstanceId"],
                "enabled": False,
                "skipTags": item.get("skipTags", []),
                "activeDownloadLimit": item.get("activeDownloadLimit", 3),
                "minCycleTimeDays": item.get("minCycleTimeDays", 7),
                "monitoredOnly": True,
                "useCutoff": False,
                "useCustomFormatScore": False,
            }
        )
    api.request(
        "/api/configuration/seeker",
        "PUT",
        {
            "searchEnabled": True,
            "searchInterval": 5,
            "proactiveSearchEnabled": False,
            "selectionStrategy": "BalancedWeighted",
            "useRoundRobin": True,
            "postReleaseGraceHours": 6,
            "instances": instances,
        },
    )


def queue_cleaner_run_counts(api: Api) -> tuple[int, int]:
    stats = api.request("/api/v2/stats?hours=1&includeDryRun=true")
    queue_stats = stats.get("jobs", {}).get("byType", {}).get("QueueCleaner", {})
    return int(queue_stats.get("completed", 0)), int(queue_stats.get("failed", 0))


def wait_for_queue_cleaner(
    api: Api, previous_completed: int, previous_failed: int
) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        completed, failed = queue_cleaner_run_counts(api)
        if failed > previous_failed:
            raise RuntimeError("Cleanuparr dry-run Queue Cleaner job failed")
        if completed > previous_completed:
            return
        time.sleep(2)
    raise RuntimeError("Cleanuparr dry-run Queue Cleaner job did not finish")


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def assert_subset(actual: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, value in expected.items():
        actual_value = canonical(actual.get(key))
        expected_value = canonical(value)
        if (
            isinstance(actual_value, str)
            and isinstance(expected_value, str)
            and expected_value.startswith(("http://", "https://"))
        ):
            actual_value = actual_value.rstrip("/")
            expected_value = expected_value.rstrip("/")
        if actual_value != expected_value:
            raise RuntimeError(f"{label} setting drifted: {key}")


def verify(api: Api, expect_dry_run: bool = False) -> None:
    general = api.request("/api/configuration/general")
    expected_general = desired_general(general, expect_dry_run)
    assert_subset(general, expected_general, "general")

    clients = api.request("/api/configuration/download_client").get("clients", [])
    matches = [item for item in clients if item.get("name") == QBITTORRENT_NAME]
    if len(matches) != 1:
        raise RuntimeError("Cleanuparr repository-owned qBittorrent client is missing")
    assert_subset(
        matches[0],
        {
            "enabled": True,
            "typeName": "qBittorrent",
            "type": "Torrent",
            "host": "http://gluetun:8080",
        },
        "qBittorrent",
    )

    for arr_type, (name, url, _external_url, version, _env_name) in ARRS.items():
        config = api.request(f"/api/configuration/{arr_type}")
        if config.get("failedImportMaxStrikes") != 0:
            raise RuntimeError(f"Cleanuparr {arr_type} failed-import policy drifted")
        matches = [
            item for item in config.get("instances", []) if item.get("name") == name
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Cleanuparr {arr_type} instance is missing")
        assert_subset(
            matches[0],
            {"enabled": True, "url": url, "version": version},
            arr_type,
        )

    queue = api.request("/api/configuration/queue_cleaner")
    assert_subset(
        queue,
        {
            "enabled": True,
            "cronExpression": "0 0/30 * ? * * *",
            "downloadingMetadataMaxStrikes": 12,
            "processNoContentId": False,
        },
        "Queue Cleaner",
    )
    if queue.get("failedImport", {}).get("maxStrikes") != 0:
        raise RuntimeError("Cleanuparr failed-import cleanup must remain disabled")

    rules = api.request("/api/queue-rules/stall")
    for name, expected in STALL_RULES.items():
        matches = [item for item in rules if item.get("name") == name]
        if len(matches) != 1:
            raise RuntimeError(f"Cleanuparr stall rule is missing: {name}")
        assert_subset(matches[0], expected, name)
    if api.request("/api/queue-rules/slow"):
        raise RuntimeError("Cleanuparr slow-download rules must remain empty")

    seeker = api.request("/api/configuration/seeker")
    assert_subset(
        seeker,
        {
            "searchEnabled": True,
            "searchInterval": 5,
            "proactiveSearchEnabled": False,
        },
        "Seeker",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    wait_for_health()
    api = Api()
    authenticate(api)
    if args.check:
        verify(api)
        print(
            "Cleanuparr API verification passed: four Arrs, qBittorrent, "
            "guarded stall rules, and replacement-only Seeker"
        )
        return 0

    current_general = api.request("/api/configuration/general")
    api.request(
        "/api/configuration/general",
        "PUT",
        desired_general(current_general, True),
    )
    upsert_download_client(api)
    upsert_arrs(api)
    upsert_stall_rules(api)
    configure_queue_and_seeker(api)
    verify(api, expect_dry_run=True)

    completed, failed = queue_cleaner_run_counts(api)
    api.request("/api/jobs/QueueCleaner/trigger", "POST")
    wait_for_queue_cleaner(api, completed, failed)

    current_general = api.request("/api/configuration/general")
    api.request(
        "/api/configuration/general",
        "PUT",
        desired_general(current_general, False),
    )
    verify(api)
    print(
        "Cleanuparr reconciled through its supported API; dry-run passed and "
        "guarded automatic cleanup is enabled"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
