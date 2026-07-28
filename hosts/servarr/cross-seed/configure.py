#!/usr/bin/env python3
"""Reconcile three private Prowlarr indexers and render cross-seed v6 config."""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Any

PROWLARR_URL = "http://192.168.0.102:9696"
PROWLARR_CONFIG = Path("/docker/prowlarr/config.xml")
CROSS_SEED_CONFIG = Path("/docker/cross-seed/config.js")
APPROVAL_FILE = Path("/docker/cross-seed/indexers-approved")
TARGETS = (
    {
        "definition": "btschool",
        "name": "BTSchool",
        "username_env": "BTSCHOOL_USERNAME",
        "password_env": "BTSCHOOL_PASSWORD",
        "two_factor_env": None,
        "priority": 1,
    },
    {
        "definition": "railgunpt",
        "name": "RailgunPT",
        "username_env": "RAILGUN_PT_USERNAME",
        "password_env": "RAILGUN_PT_PASSWORD",
        "two_factor_env": "RAILGUN_PT_2FA_CODE",
        "priority": 2,
    },
    {
        "definition": "hdclone",
        "name": "HDClone",
        "username_env": "HDCLONE_TOP_USERNAME",
        "password_env": "HDCLONE_TOP_PASSWORD",
        "two_factor_env": "HDCLONE_TOP_2FA_CODE",
        "priority": 3,
    },
)


class ConfigurationError(RuntimeError):
    """A safe-to-display configuration failure."""


def require_environment() -> None:
    for target in TARGETS:
        for key in (target["username_env"], target["password_env"]):
            value = os.environ.get(str(key), "")
            if not value.strip():
                raise ConfigurationError(f"{key} is missing or empty")
            if "\n" in value or "\r" in value:
                raise ConfigurationError(f"{key} contains a newline")


def prowlarr_api_key() -> str:
    if not PROWLARR_CONFIG.is_file():
        raise ConfigurationError("Prowlarr configuration is missing")
    try:
        key = ElementTree.parse(PROWLARR_CONFIG).getroot().findtext("ApiKey", "")
    except ElementTree.ParseError as error:
        raise ConfigurationError("Prowlarr configuration is invalid XML") from error
    if not key:
        raise ConfigurationError("Prowlarr API key is missing")
    return key


def api_request(
    api_key: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
) -> Any:
    data = None
    headers = {"Accept": "application/json", "X-Api-Key": api_key}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{PROWLARR_URL}/api/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        safe_path = path.split("?", 1)[0]
        raise ConfigurationError(
            f"Prowlarr {method} {safe_path} returned HTTP {error.code}"
        ) from error
    except urllib.error.URLError as error:
        raise ConfigurationError(
            f"Prowlarr {method} {path.split('?', 1)[0]} was unreachable"
        ) from error
    return json.loads(body) if body else None


def field_map(resource: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(field.get("name")): field
        for field in resource.get("fields", [])
        if field.get("name")
    }


def definition_name(resource: dict[str, Any]) -> str:
    return str(field_map(resource).get("definitionFile", {}).get("value", ""))


def set_field(resource: dict[str, Any], name: str, value: Any) -> None:
    fields = field_map(resource)
    if name not in fields:
        raise ConfigurationError(
            f"Prowlarr definition {definition_name(resource)} lacks field {name}"
        )
    fields[name]["value"] = value


def target_environment(target: dict[str, Any]) -> tuple[str, str, str]:
    username = os.environ[str(target["username_env"])]
    password = os.environ[str(target["password_env"])]
    two_factor_key = target.get("two_factor_env")
    two_factor = os.environ.get(str(two_factor_key), "") if two_factor_key else ""
    return username, password, two_factor


def app_profile_id(api_key: str) -> int:
    profiles = api_request(api_key, "appprofile")
    candidates = [
        profile
        for profile in profiles
        if profile.get("enableRss")
        and profile.get("enableAutomaticSearch")
        and profile.get("enableInteractiveSearch")
        and profile.get("seedRatio") is None
        and profile.get("seedTime") is None
        and profile.get("packSeedTime") is None
    ]
    if len(candidates) != 1:
        raise ConfigurationError(
            "expected exactly one Prowlarr profile with all searches enabled "
            "and unlimited seeding"
        )
    return int(candidates[0]["id"])


def desired_resource(
    source: dict[str, Any],
    target: dict[str, Any],
    profile_id: int,
    *,
    enabled: bool,
) -> dict[str, Any]:
    resource = copy.deepcopy(source)
    username, password, two_factor = target_environment(target)
    resource["name"] = target["name"]
    resource["enable"] = enabled
    resource["redirect"] = False
    resource["appProfileId"] = profile_id
    resource["priority"] = target["priority"]
    resource["tags"] = []
    set_field(resource, "username", username)
    set_field(resource, "password", password)
    set_field(resource, "freeleech", False)
    set_field(resource, "torrentBaseSettings.seedRatio", None)
    set_field(resource, "torrentBaseSettings.seedTime", None)
    set_field(resource, "torrentBaseSettings.packSeedTime", None)
    if "2facode" in field_map(resource):
        set_field(resource, "2facode", two_factor)
    return resource


def resources_by_definition(
    resources: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for resource in resources:
        grouped.setdefault(definition_name(resource), []).append(resource)
    return grouped


def reconcile_indexers(api_key: str) -> list[dict[str, Any]]:
    profile_id = app_profile_id(api_key)
    schemas = resources_by_definition(api_request(api_key, "indexer/schema"))
    existing = resources_by_definition(api_request(api_key, "indexer"))
    reconciled: list[dict[str, Any]] = []
    approved = APPROVAL_FILE.is_file()

    for target in TARGETS:
        definition = str(target["definition"])
        schema_rows = schemas.get(definition, [])
        existing_rows = existing.get(definition, [])
        if len(schema_rows) != 1:
            raise ConfigurationError(
                f"expected one Prowlarr schema for {definition}, found {len(schema_rows)}"
            )
        if len(existing_rows) > 1:
            raise ConfigurationError(
                f"multiple Prowlarr indexers use definition {definition}"
            )

        source = existing_rows[0] if existing_rows else schema_rows[0]
        # Prowlarr tests an enabled indexer even on a force-saved create. New
        # resources must therefore be created disabled, then enabled through a
        # force-saved update only after the manual approval marker exists.
        desired = desired_resource(
            source,
            target,
            profile_id,
            enabled=approved if existing_rows else False,
        )
        if existing_rows:
            indexer_id = int(existing_rows[0]["id"])
            saved = api_request(
                api_key,
                f"indexer/{indexer_id}?forceSave=true",
                method="PUT",
                payload=desired,
            )
            action = "reconciled"
        else:
            desired.pop("id", None)
            saved = api_request(
                api_key,
                "indexer?forceSave=true",
                method="POST",
                payload=desired,
            )
            action = "created"
            if approved:
                desired = desired_resource(
                    saved,
                    target,
                    profile_id,
                    enabled=True,
                )
                saved = api_request(
                    api_key,
                    f"indexer/{int(saved['id'])}?forceSave=true",
                    method="PUT",
                    payload=desired,
                )
        reconciled.append(saved)
        state = "enabled" if approved else "disabled pending manual approval"
        print(
            f"{target['name']} Prowlarr indexer {action} without a login test; "
            f"{state}"
        )
    return reconciled


def current_targets(api_key: str) -> list[dict[str, Any]]:
    grouped = resources_by_definition(api_request(api_key, "indexer"))
    resources: list[dict[str, Any]] = []
    for target in TARGETS:
        rows = grouped.get(str(target["definition"]), [])
        if len(rows) != 1:
            raise ConfigurationError(
                f"expected one configured {target['name']} indexer, found {len(rows)}"
            )
        resources.append(rows[0])
    return resources


def test_indexers(api_key: str) -> None:
    # This is deliberately explicit and single-shot: each invocation performs
    # exactly one Prowlarr-supported login/search test per configured tracker.
    for target, resource in zip(TARGETS, current_targets(api_key), strict=True):
        api_request(
            api_key,
            "indexer/test",
            method="POST",
            payload=resource,
            timeout=180,
        )
        print(f"{target['name']} passed one Prowlarr indexer test")


def config_text(api_key: str, resources: list[dict[str, Any]]) -> str:
    indexer_ids = {
        definition_name(resource): int(resource["id"]) for resource in resources
    }
    torznab = [
        f"http://gluetun:9696/{indexer_ids[str(target['definition'])]}/api"
        f"?apikey={api_key}"
        for target in TARGETS
    ]
    torznab_lines = "\n".join(f"        {json.dumps(url)}," for url in torznab)
    return f'''"use strict";
// Rendered from Git by configure.py. Contains a Prowlarr API key; mode 0600.
module.exports = {{
    apiKey: undefined,
    torznab: [
{torznab_lines}
    ],
    sonarr: [],
    radarr: [],
    host: "0.0.0.0",
    port: 2468,
    notificationWebhookUrls: [],
    torrentClients: ["qbittorrent:http://gluetun:8080"],
    useClientTorrents: true,
    delay: 60,
    dataDirs: [],
    linkCategory: "cross-seed-link",
    linkDirs: ["/data/torrents/cross-seed-links"],
    linkType: "hardlink",
    flatLinking: false,
    matchMode: "strict",
    skipRecheck: false,
    autoResumeMaxDownload: 0,
    ignoreNonRelevantFilesToResume: false,
    maxDataDepth: 2,
    torrentDir: null,
    outputDir: null,
    includeSingleEpisodes: false,
    includeNonVideos: true,
    seasonFromEpisodes: null,
    fuzzySizeThreshold: 0.02,
    excludeOlder: "150 days",
    excludeRecentSearch: "30 days",
    action: "inject",
    duplicateCategories: false,
    rssCadence: "1 hour",
    searchCadence: "1 day",
    snatchTimeout: "30 seconds",
    searchTimeout: "2 minutes",
    searchLimit: 50,
    blockList: [],
}};
'''


def render_config(api_key: str, resources: list[dict[str, Any]]) -> None:
    CROSS_SEED_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    content = config_text(api_key, resources)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".config.js.", dir=CROSS_SEED_CONFIG.parent
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chown(temporary, 1000, 1000)
        os.replace(temporary, CROSS_SEED_CONFIG)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    print("cross-seed strict configuration rendered without tracker credentials")


def validate_resources(
    api_key: str,
    *,
    expected_enabled: bool,
) -> list[dict[str, Any]]:
    profile_id = app_profile_id(api_key)
    resources = current_targets(api_key)
    for target, resource in zip(TARGETS, resources, strict=True):
        if resource.get("name") != target["name"]:
            raise ConfigurationError(f"{target['name']} name drifted")
        if bool(resource.get("enable")) is not expected_enabled:
            state = "enabled" if expected_enabled else "disabled"
            raise ConfigurationError(f"{target['name']} is not {state}")
        if int(resource.get("priority", -1)) != int(target["priority"]):
            raise ConfigurationError(f"{target['name']} priority drifted")
        if int(resource.get("appProfileId", -1)) != profile_id:
            raise ConfigurationError(f"{target['name']} app profile drifted")
        fields = field_map(resource)
        username, _, _ = target_environment(target)
        if fields.get("username", {}).get("value") != username:
            raise ConfigurationError(f"{target['name']} username drifted")
        if not fields.get("password", {}).get("value"):
            raise ConfigurationError(f"{target['name']} password is absent")
        if fields.get("freeleech", {}).get("value") is not False:
            raise ConfigurationError(f"{target['name']} freeleech-only drifted")
        for field_name in (
            "torrentBaseSettings.seedRatio",
            "torrentBaseSettings.seedTime",
            "torrentBaseSettings.packSeedTime",
        ):
            if fields.get(field_name, {}).get("value") is not None:
                raise ConfigurationError(
                    f"{target['name']} has a stopping seed limit"
                )
    return resources


def check_configuration(api_key: str) -> None:
    approved = APPROVAL_FILE.is_file()
    resources = validate_resources(api_key, expected_enabled=approved)

    if not CROSS_SEED_CONFIG.is_file():
        raise ConfigurationError("cross-seed config.js is missing")
    if CROSS_SEED_CONFIG.stat().st_mode & 0o077:
        raise ConfigurationError("cross-seed config.js is not mode 0600")
    content = CROSS_SEED_CONFIG.read_text(encoding="utf-8")
    expected = config_text(api_key, resources)
    if content != expected:
        raise ConfigurationError("cross-seed config.js drifted")
    state = "approved and enabled" if approved else "disabled pending approval"
    print(
        f"cross-seed configuration check passed: three indexers {state}, "
        "strict hardlink matching, unlimited seeding, and zero-byte auto-resume"
    )


def approve_configuration(api_key: str) -> None:
    resources = validate_resources(api_key, expected_enabled=True)
    render_config(api_key, resources)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".indexers-approved.", dir=APPROVAL_FILE.parent
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write("All three Prowlarr indexers manually tested and approved.\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chown(temporary, 1000, 1000)
        os.replace(temporary, APPROVAL_FILE)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    print("cross-seed manual indexer approval recorded")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--approve", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--test", action="store_true")
    arguments = parser.parse_args()

    try:
        require_environment()
        api_key = prowlarr_api_key()
        if arguments.approve:
            approve_configuration(api_key)
        elif arguments.check:
            check_configuration(api_key)
        elif arguments.test:
            test_indexers(api_key)
        else:
            resources = reconcile_indexers(api_key)
            render_config(api_key, resources)
    except ConfigurationError as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
