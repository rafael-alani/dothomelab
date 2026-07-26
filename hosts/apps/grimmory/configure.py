#!/usr/bin/env python3
"""Initialize Grimmory and reconcile its fail-closed canonical metadata policy."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://192.168.0.112:6060/api/v1"
LIBRARIES = (
    {
        "name": "Canonical Ebooks",
        "paths": [{"path": "/library/ebooks"}],
        "watch": True,
        "formatPriority": ["EPUB"],
        "allowedFormats": ["EPUB"],
        "metadataSource": "PREFER_EMBEDDED",
        "organizationMode": "BOOK_PER_FILE",
    },
    {
        "name": "Canonical Audiobooks",
        "paths": [{"path": "/library/audiobooks"}],
        "watch": True,
        "formatPriority": ["AUDIOBOOK"],
        "allowedFormats": ["AUDIOBOOK"],
        "metadataSource": "PREFER_EMBEDDED",
        "organizationMode": "BOOK_PER_FOLDER",
    },
)


def request(
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    token: str | None = None,
) -> object:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Grimmory {method} {path} returned {error.code}: {detail[:500]}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Grimmory {method} {path} could not be reached") from error
    return json.loads(body) if body else {}


def login() -> str:
    response = request(
        "/auth/login",
        method="POST",
        payload={
            "username": os.environ["GRIMMORY_ADMIN_USERNAME"],
            "password": os.environ["GRIMMORY_ADMIN_PASSWORD"],
        },
    )
    if not isinstance(response, dict) or not response.get("accessToken"):
        raise RuntimeError("Grimmory login returned no access token")
    return str(response["accessToken"])


def wait_for_api() -> None:
    last_error: Exception | None = None
    for _ in range(90):
        try:
            request("/healthcheck")
            return
        except RuntimeError as error:
            last_error = error
            time.sleep(2)
    raise RuntimeError("Grimmory API did not become ready within 180 seconds") from last_error


def configure_settings(token: str, libraries: list[dict[str, object]]) -> None:
    settings = request("/settings", token=token)
    if not isinstance(settings, dict):
        raise RuntimeError("Grimmory returned invalid settings")

    providers = copy.deepcopy(settings.get("metadataProviderSettings") or {})
    providers.update(
        {
            "amazon": {
                **providers.get("amazon", {}),
                "enabled": True,
                "domain": "com",
            },
            "google": {
                **providers.get("google", {}),
                "enabled": True,
                "language": "en",
            },
            "goodReads": {"enabled": True},
            "hardcover": {
                **providers.get("hardcover", {}),
                "enabled": False,
                "apiKey": None,
            },
            "audible": {"enabled": True, "domain": "com"},
        }
    )

    persistence = {
        "saveToOriginalFile": {
            "epub": {"enabled": True, "maxFileSizeInMb": 250},
            "pdf": {"enabled": False, "maxFileSizeInMb": 250},
            "cbx": {"enabled": False, "maxFileSizeInMb": 250},
            "audiobook": {"enabled": True, "maxFileSizeInMb": 10240},
        },
        "convertCbrCb7ToCbz": False,
        "moveFilesToLibraryPattern": False,
        "sidecarSettings": {
            "enabled": True,
            "writeOnUpdate": True,
            "writeOnScan": True,
            "includeCoverFile": True,
        },
    }

    default_options = copy.deepcopy(settings["defaultMetadataRefreshOptions"])
    default_options.update(
        {
            "libraryId": None,
            "refreshCovers": True,
            "mergeCategories": True,
            "reviewBeforeApply": True,
            "replaceMode": "REPLACE_WHEN_PROVIDED",
        }
    )

    library_options: list[dict[str, object]] = []
    for library in libraries:
        options = copy.deepcopy(default_options)
        options["libraryId"] = library["id"]
        if library["name"] == "Canonical Audiobooks":
            field_options = options["fieldOptions"]
            for key in (
                "title",
                "subtitle",
                "description",
                "authors",
                "publisher",
                "publishedDate",
                "seriesName",
                "seriesNumber",
                "language",
                "categories",
                "cover",
                "asin",
                "audibleId",
            ):
                field_options[key] = {
                    "p1": "Audible",
                    "p2": "GoodReads",
                    "p3": "Google",
                    "p4": "Amazon",
                }
        library_options.append(options)

    request(
        "/settings",
        method="PUT",
        token=token,
        payload=[
            {"name": "METADATA_PROVIDER_SETTINGS", "value": providers},
            {"name": "METADATA_PERSISTENCE_SETTINGS", "value": persistence},
            {"name": "QUICK_BOOK_MATCH", "value": default_options},
            {
                "name": "LIBRARY_METADATA_REFRESH_OPTIONS",
                "value": library_options,
            },
        ],
    )


def reconcile_libraries(token: str) -> list[dict[str, object]]:
    response = request("/libraries", token=token)
    if not isinstance(response, list):
        raise RuntimeError("Grimmory returned an invalid library list")
    existing = {item["name"]: item for item in response}
    reconciled: list[dict[str, object]] = []
    for desired in LIBRARIES:
        current = existing.get(desired["name"])
        if current:
            library = request(
                f"/libraries/{current['id']}",
                method="PUT",
                payload=desired,
                token=token,
            )
        else:
            library = request(
                "/libraries", method="POST", payload=desired, token=token
            )
        if not isinstance(library, dict) or not library.get("id"):
            raise RuntimeError(f"Grimmory failed to reconcile {desired['name']}")
        reconciled.append(library)
    return reconciled


def verify(token: str) -> None:
    settings = request("/settings", token=token)
    libraries = request("/libraries", token=token)
    expected = {item["name"]: item for item in LIBRARIES}
    actual = {item["name"]: item for item in libraries if item["name"] in expected}
    if set(actual) != set(expected):
        raise RuntimeError("Grimmory canonical libraries are missing or duplicated")
    for name, desired in expected.items():
        library = actual[name]
        paths = [item["path"] for item in library["paths"]]
        if paths != [desired["paths"][0]["path"]]:
            raise RuntimeError(f"{name} path drifted")
        for key in (
            "watch",
            "formatPriority",
            "allowedFormats",
            "metadataSource",
            "organizationMode",
        ):
            if library.get(key) != desired[key]:
                raise RuntimeError(f"{name} setting drifted: {key}")

    persistence = settings["metadataPersistenceSettings"]
    write = persistence["saveToOriginalFile"]
    if not write["epub"]["enabled"] or not write["audiobook"]["enabled"]:
        raise RuntimeError("Grimmory canonical file writing is not enabled")
    if write["pdf"]["enabled"] or write["cbx"]["enabled"]:
        raise RuntimeError("Grimmory non-canonical format writing is enabled")
    if persistence["moveFilesToLibraryPattern"]:
        raise RuntimeError("Grimmory automatic file moving is enabled")
    sidecars = persistence["sidecarSettings"]
    if not all(
        sidecars[key]
        for key in ("enabled", "writeOnUpdate", "writeOnScan", "includeCoverFile")
    ):
        raise RuntimeError("Grimmory sidecar policy drifted")

    options = settings["libraryMetadataRefreshOptions"]
    by_id = {item["libraryId"]: item for item in options}
    for library in actual.values():
        if not by_id.get(library["id"], {}).get("reviewBeforeApply"):
            raise RuntimeError(f"{library['name']} is not fail closed")
    print(
        "Grimmory canonical libraries, writable formats, sidecars, "
        "and review-before-apply policy verified"
    )


def main() -> int:
    check = "--check" in sys.argv[1:]
    wait_for_api()
    status = request("/setup/status")
    completed = bool(status.get("data")) if isinstance(status, dict) else False
    if not completed:
        if check:
            raise RuntimeError("Grimmory initial setup is incomplete")
        request(
            "/setup",
            method="POST",
            payload={
                "username": os.environ["GRIMMORY_ADMIN_USERNAME"],
                "email": os.environ["GRIMMORY_ADMIN_EMAIL"],
                "name": os.environ["GRIMMORY_ADMIN_NAME"],
                "password": os.environ["GRIMMORY_ADMIN_PASSWORD"],
            },
        )

    token = login()
    if check:
        verify(token)
        return 0

    libraries = reconcile_libraries(token)
    configure_settings(token, libraries)
    for library in libraries:
        request(f"/libraries/{library['id']}/refresh", method="PUT", token=token)
    verify(token)
    print("Grimmory administrator, libraries, native metadata policy, and scans reconciled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
