#!/usr/bin/env python3
"""Remove confirmed retired Prowlarr indexers and audit supported definitions."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

DEFAULT_PROWLARR_URL = "http://192.168.0.102:9696"
DEFAULT_CONFIG_PATH = "/docker/prowlarr/config.xml"

# These public Cardigann definitions were absent from Prowlarr 2.5.2's live
# schema catalog on 2026-07-28. Names and definition IDs must both match before
# the reconciler removes an entry. Credentialed private trackers are never
# listed here and unexpected future removals fail closed.
RETIRED_PUBLIC_INDEXERS = {
    "Badass Torrents": "badasstorrents",
    "BitSearch": "bitsearch",
    "GloDLS": "glodls",
    "iDope": "idope",
    "NyaaPantsu": "nyaapantsu",
    "Solid Torrents": "solidtorrents",
    "TheRARBG": "therarbg",
    "Torlock": "torlock",
    "YourBittorrent": "yourbittorrent",
}

# Prowlarr applies a tagged FlareSolverr proxy only to indexers carrying the
# same tag. These supported public definitions returned Cloudflare protection
# responses during the 2026-07-28 live audit.
FLARESOLVERR_INDEXERS = {
    "1337x": "1337x",
    "ExtraTorrent.st": "extratorrent-st",
    "EZTV": "eztv",
    "Magnet Cat": "magnetcat",
    "Torrent[CORE]": "torrentcore",
}
FLARESOLVERR_TAG = "flaresolverr"

# These definitions still exist upstream but failed one explicit Prowlarr test
# on their configured URL and one schema-declared alternative (where offered).
# Keeping them disabled preserves their configuration without allowing
# repeated failures to delay searches or trigger long backoff warnings.
UNAVAILABLE_PUBLIC_INDEXERS = {
    "1337x": "1337x",
    "EBookBay": "ebookbay",
    "ExtraTorrent.st": "extratorrent-st",
    "EZTV": "eztv",
    "Magnet Cat": "magnetcat",
    "Torrent[CORE]": "torrentcore",
    "Torrent Downloads": "torrentdownloads",
}


class ReconcileError(RuntimeError):
    """Raised when live Prowlarr state is unsafe to mutate."""


def api_key(config_path: str) -> str:
    try:
        key = ET.parse(config_path).findtext("ApiKey", "")
    except (ET.ParseError, OSError) as error:
        raise ReconcileError(
            f"Prowlarr configuration is unavailable: {config_path}"
        ) from error
    if not key:
        raise ReconcileError("Prowlarr API key is missing")
    return key


def api_request(
    base_url: str,
    key: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v1/{path.lstrip('/')}",
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Api-Key": key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise ReconcileError(
            f"Prowlarr {method} {path.split('?', 1)[0]} returned "
            f"HTTP {error.code}"
        ) from error
    except urllib.error.URLError as error:
        raise ReconcileError(
            f"Prowlarr {method} {path.split('?', 1)[0]} was unreachable"
        ) from error
    return json.loads(body) if body else None


def wait_for_api(base_url: str, key: str, wait_seconds: int) -> None:
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            api_request(
                base_url,
                key,
                "system/status",
                timeout=5,
            )
            return
        except ReconcileError:
            if time.monotonic() >= deadline:
                raise ReconcileError(
                    f"Prowlarr API did not become ready within {wait_seconds} seconds"
                )
            time.sleep(2)


def field_value(resource: dict[str, Any], name: str) -> Any:
    return next(
        (
            field.get("value")
            for field in resource.get("fields", [])
            if field.get("name") == name
        ),
        None,
    )


def set_field_value(resource: dict[str, Any], name: str, value: Any) -> None:
    field = next(
        (
            field
            for field in resource.get("fields", [])
            if field.get("name") == name
        ),
        None,
    )
    if field is None:
        raise ReconcileError(
            f"Prowlarr definition {definition_name(resource)} lacks field {name}"
        )
    field["value"] = value


def definition_name(resource: dict[str, Any]) -> str:
    return str(field_value(resource, "definitionFile") or "")


def indexer_catalog(
    base_url: str, key: str
) -> tuple[list[dict[str, Any]], set[str]]:
    configured = api_request(base_url, key, "indexer")
    schemas = api_request(base_url, key, "indexer/schema")
    if not isinstance(configured, list) or not isinstance(schemas, list):
        raise ReconcileError("Prowlarr returned an invalid indexer catalog")
    supported = {
        definition_name(resource)
        for resource in schemas
        if definition_name(resource)
    }
    return configured, supported


def orphaned_cardigann(
    configured: list[dict[str, Any]], supported: set[str]
) -> list[dict[str, Any]]:
    return [
        resource
        for resource in configured
        if resource.get("implementation") == "Cardigann"
        and definition_name(resource)
        and definition_name(resource) not in supported
    ]


def validated_retired(
    orphaned: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    known: list[dict[str, Any]] = []
    unexpected: list[str] = []
    for resource in orphaned:
        name = str(resource.get("name") or "")
        definition = definition_name(resource)
        if RETIRED_PUBLIC_INDEXERS.get(name) == definition:
            known.append(resource)
        else:
            unexpected.append(f"{name} ({definition})")
    if unexpected:
        raise ReconcileError(
            "unexpected unsupported Prowlarr definitions require manual "
            f"review: {', '.join(sorted(unexpected))}"
        )
    return known


def check_catalog(base_url: str, key: str) -> list[dict[str, Any]]:
    configured, supported = indexer_catalog(base_url, key)
    orphaned = orphaned_cardigann(configured, supported)
    if orphaned:
        detail = ", ".join(
            sorted(
                f"{resource.get('name')} ({definition_name(resource)})"
                for resource in orphaned
            )
        )
        raise ReconcileError(
            f"Prowlarr has unsupported configured definitions: {detail}"
        )
    print(
        "Prowlarr indexer catalog passed: "
        f"{len(configured)} configured, {len(supported)} supported definitions."
    )
    return configured


def apply_retired(base_url: str, key: str) -> None:
    configured, supported = indexer_catalog(base_url, key)
    orphaned = orphaned_cardigann(configured, supported)
    retired = validated_retired(orphaned)
    for resource in retired:
        resource_id = int(resource["id"])
        name = str(resource["name"])
        api_request(
            base_url,
            key,
            f"indexer/{resource_id}",
            method="DELETE",
        )
        print(f"Removed retired public Prowlarr indexer: {name}")
    if not retired:
        print("No retired public Prowlarr indexers required removal.")


def flaresolverr_tag_id(base_url: str, key: str) -> int:
    tags = api_request(base_url, key, "tag")
    matching = [
        tag for tag in tags if str(tag.get("label", "")).lower() == FLARESOLVERR_TAG
    ]
    if len(matching) != 1:
        raise ReconcileError(
            f"expected one Prowlarr tag named {FLARESOLVERR_TAG}, "
            f"found {len(matching)}"
        )
    return int(matching[0]["id"])


def flaresolverr_targets(
    configured: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for resource in configured:
        name = str(resource.get("name") or "")
        expected_definition = FLARESOLVERR_INDEXERS.get(name)
        if not expected_definition:
            continue
        definition = definition_name(resource)
        if definition != expected_definition:
            raise ReconcileError(
                f"Prowlarr indexer {name} uses unexpected definition {definition}"
            )
        targets.append(resource)
    return targets


def reconcile_flaresolverr_tags(
    base_url: str,
    key: str,
    configured: list[dict[str, Any]],
) -> None:
    tag_id = flaresolverr_tag_id(base_url, key)
    changed = 0
    for resource in flaresolverr_targets(configured):
        tags = {int(value) for value in resource.get("tags", [])}
        if tag_id in tags:
            continue
        tags.add(tag_id)
        resource["tags"] = sorted(tags)
        api_request(
            base_url,
            key,
            f"indexer/{int(resource['id'])}?forceSave=true",
            method="PUT",
            payload=resource,
        )
        changed += 1
        print(f"Applied FlareSolverr tag to Prowlarr indexer: {resource['name']}")
    if not changed:
        print("Prowlarr FlareSolverr indexer tags already match desired state.")


def check_flaresolverr_tags(
    base_url: str,
    key: str,
    configured: list[dict[str, Any]],
) -> None:
    targets = flaresolverr_targets(configured)
    if not targets:
        return
    tag_id = flaresolverr_tag_id(base_url, key)
    missing = sorted(
        str(resource["name"])
        for resource in targets
        if tag_id not in {int(value) for value in resource.get("tags", [])}
    )
    if missing:
        raise ReconcileError(
            "Prowlarr Cloudflare-protected indexers lack the FlareSolverr "
            f"tag: {', '.join(missing)}"
        )
    print(
        "Prowlarr FlareSolverr tags passed: "
        f"{len(targets)} protected indexers."
    )


def unavailable_targets(
    configured: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for resource in configured:
        name = str(resource.get("name") or "")
        expected_definition = UNAVAILABLE_PUBLIC_INDEXERS.get(name)
        if not expected_definition:
            continue
        definition = definition_name(resource)
        if definition != expected_definition:
            raise ReconcileError(
                f"Prowlarr indexer {name} uses unexpected definition {definition}"
            )
        targets.append(resource)
    return targets


def reconcile_unavailable(
    base_url: str,
    key: str,
    configured: list[dict[str, Any]],
) -> None:
    changed = 0
    for resource in unavailable_targets(configured):
        if resource.get("enable") is False:
            continue
        resource["enable"] = False
        api_request(
            base_url,
            key,
            f"indexer/{int(resource['id'])}?forceSave=true",
            method="PUT",
            payload=resource,
        )
        changed += 1
        print(f"Disabled unavailable public Prowlarr indexer: {resource['name']}")
    if not changed:
        print("Unavailable public Prowlarr indexers are already disabled.")


def check_unavailable(configured: list[dict[str, Any]]) -> None:
    targets = unavailable_targets(configured)
    enabled = sorted(
        str(resource["name"])
        for resource in targets
        if resource.get("enable") is not False
    )
    if enabled:
        raise ReconcileError(
            "confirmed unavailable public Prowlarr indexers are enabled: "
            f"{', '.join(enabled)}"
        )
    print(
        "Prowlarr unavailable-indexer policy passed: "
        f"{len(targets)} retained disabled."
    )


def safe_test_failure(error: ReconcileError) -> str:
    message = str(error)
    message = re.sub(r"https?://\S+", "[URL]", message)
    message = re.sub(
        r"(?i)(api[_-]?key|passkey|token|password|username)=?\S*",
        r"\1=[REDACTED]",
        message,
    )
    return message


def test_indexers(
    base_url: str,
    key: str,
    configured: list[dict[str, Any]],
    names: list[str],
) -> None:
    by_name = {str(resource.get("name")): resource for resource in configured}
    missing = sorted(set(names) - set(by_name))
    if missing:
        raise ReconcileError(
            f"requested Prowlarr indexers are not configured: {', '.join(missing)}"
        )
    failed: list[str] = []
    for name in names:
        try:
            api_request(
                base_url,
                key,
                "indexer/test",
                method="POST",
                payload=by_name[name],
                timeout=120,
            )
        except ReconcileError as error:
            print(
                f"FAIL Prowlarr indexer test: {name}: "
                f"{safe_test_failure(error)}",
                file=sys.stderr,
            )
            failed.append(name)
        else:
            print(f"PASS Prowlarr indexer test: {name}")
    if failed:
        raise ReconcileError(
            f"{len(failed)} Prowlarr indexer test(s) failed: "
            f"{', '.join(failed)}"
        )


def probe_base_urls(
    base_url: str,
    key: str,
    configured: list[dict[str, Any]],
    probes: list[str],
) -> None:
    schemas = api_request(base_url, key, "indexer/schema")
    schema_by_definition = {
        definition_name(resource): resource
        for resource in schemas
        if definition_name(resource)
    }
    configured_by_name = {
        str(resource.get("name")): resource for resource in configured
    }
    failed: list[str] = []
    for probe in probes:
        if "=" not in probe:
            raise ReconcileError(
                f"base URL probe must use INDEXER=URL syntax: {probe}"
            )
        name, candidate = probe.split("=", 1)
        resource = configured_by_name.get(name)
        if resource is None:
            raise ReconcileError(f"Prowlarr indexer is not configured: {name}")
        schema = schema_by_definition.get(definition_name(resource))
        if schema is None:
            raise ReconcileError(
                f"Prowlarr definition is unsupported: {definition_name(resource)}"
            )
        declared_urls = set(schema.get("indexerUrls", []))
        declared_urls.update(schema.get("legacyUrls", []))
        if candidate not in declared_urls:
            raise ReconcileError(
                f"Prowlarr does not declare candidate URL for {name}"
            )
        candidate_resource = copy.deepcopy(resource)
        set_field_value(candidate_resource, "baseUrl", candidate)
        try:
            api_request(
                base_url,
                key,
                "indexer/test",
                method="POST",
                payload=candidate_resource,
                timeout=120,
            )
        except ReconcileError as error:
            print(
                f"FAIL Prowlarr declared base URL probe: {name}: "
                f"{safe_test_failure(error)}",
                file=sys.stderr,
            )
            failed.append(name)
        else:
            print(f"PASS Prowlarr declared base URL probe: {name}")
    if failed:
        raise ReconcileError(
            f"{len(failed)} Prowlarr base URL probe(s) failed: "
            f"{', '.join(failed)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--apply",
        action="store_true",
        help="reconcile retired definitions, FlareSolverr tags, and disabled set",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="fail if any configured Cardigann definition is unsupported",
    )
    parser.add_argument(
        "--test",
        action="append",
        default=[],
        metavar="INDEXER",
        help="run one explicit Prowlarr-supported test by exact indexer name",
    )
    parser.add_argument(
        "--probe-base-url",
        action="append",
        default=[],
        metavar="INDEXER=URL",
        help="test, but do not save, a Prowlarr-declared base URL",
    )
    parser.add_argument("--url", default=DEFAULT_PROWLARR_URL)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--wait-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        key = api_key(args.config)
        wait_for_api(args.url, key, args.wait_seconds)
        if args.apply:
            apply_retired(args.url, key)
            configured, _ = indexer_catalog(args.url, key)
            reconcile_flaresolverr_tags(args.url, key, configured)
            configured, _ = indexer_catalog(args.url, key)
            reconcile_unavailable(args.url, key, configured)
        configured = check_catalog(args.url, key)
        check_flaresolverr_tags(args.url, key, configured)
        check_unavailable(configured)
        if args.test:
            test_indexers(args.url, key, configured, args.test)
        if args.probe_base_url:
            probe_base_urls(
                args.url,
                key,
                configured,
                args.probe_base_url,
            )
    except ReconcileError as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
