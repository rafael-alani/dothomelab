#!/usr/bin/env python3
"""Install deterministic Cardigann identities for the cross-seed proxy."""

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
DEFINITION_DIR = Path("/docker/prowlarr/Definitions")
CUSTOM_DIR = DEFINITION_DIR / "Custom"
TARGETS = {
    "btschool": {
        "custom_definition": "dothomelab-btschool",
        "display_name": "BTSCHOOL",
        "schema_name": "BTSCHOOL (dothomelab)",
    },
    "railgunpt": {
        "custom_definition": "dothomelab-railgunpt",
        "display_name": "RailgunPT",
        "schema_name": "RailgunPT (dothomelab)",
    },
}
DESCRIPTION_PREFIX = "dothomelab cross-seed proxy definition for "


class DefinitionError(RuntimeError):
    """A safe-to-display reconciliation failure."""


def field_map(resource: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(field.get("name")): field
        for field in resource.get("fields", [])
        if field.get("name")
    }


def definition_name(resource: dict[str, Any]) -> str:
    return str(field_map(resource).get("definitionFile", {}).get("value", ""))


def prowlarr_api_key() -> str:
    try:
        key = ElementTree.parse(PROWLARR_CONFIG).getroot().findtext("ApiKey", "")
    except (ElementTree.ParseError, OSError) as error:
        raise DefinitionError("Prowlarr configuration is unavailable") from error
    if not key:
        raise DefinitionError("Prowlarr API key is missing")
    return key


def api_request(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{PROWLARR_URL}/api/v1/{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Api-Key": prowlarr_api_key(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as error:
        raise DefinitionError(
            f"Prowlarr {method} {path.split('?', 1)[0]} failed"
        ) from error
    return json.loads(body) if body else None


def description_line(display_name: str) -> str:
    return f'description: "{DESCRIPTION_PREFIX}{display_name}"'


def set_field(resource: dict[str, Any], name: str, value: Any) -> None:
    fields = field_map(resource)
    if name not in fields:
        raise DefinitionError(
            f"Prowlarr definition {definition_name(resource)} lacks field {name}"
        )
    fields[name]["value"] = value


def render_definition(
    source_definition: str,
    custom_definition: str,
    display_name: str,
    schema_name: str,
) -> str:
    source_path = DEFINITION_DIR / f"{source_definition}.yml"
    if not source_path.is_file():
        raise DefinitionError(
            f"bundled definition is missing: {source_definition}"
        )
    source = source_path.read_text(encoding="utf-8")
    if source.count(f"id: {source_definition}\n") != 1:
        raise DefinitionError(f"bundled {source_definition} ID drifted")
    if source.count("\nsearch:\n") != 1:
        raise DefinitionError(
            f"bundled {source_definition} search block drifted"
        )
    if "\ndownload:\n" in source:
        raise DefinitionError(
            f"bundled {source_definition} now has a download block; review "
            "and retire the local override"
        )
    if 'selector: a[href^="download.php?id="]' not in source:
        raise DefinitionError(
            f"bundled {source_definition} download selector drifted"
        )

    lines = source.splitlines()
    id_indexes = [
        index for index, line in enumerate(lines) if line == f"id: {source_definition}"
    ]
    name_indexes = [
        index
        for index, line in enumerate(lines)
        if line == f"name: {display_name}"
    ]
    description_indexes = [
        index for index, line in enumerate(lines) if line.startswith("description:")
    ]
    if len(id_indexes) != 1 or len(name_indexes) != 1:
        raise DefinitionError(
            f"bundled {source_definition} identity fields drifted"
        )
    if len(description_indexes) != 1:
        raise DefinitionError(
            f"bundled {source_definition} description drifted"
        )
    lines[id_indexes[0]] = f"id: {custom_definition}"
    lines[name_indexes[0]] = f"name: {schema_name}"
    lines[description_indexes[0]] = description_line(display_name)
    source = "\n".join(lines) + "\n"
    return source


def expected_definitions() -> dict[Path, str]:
    return {
        CUSTOM_DIR / f"{target['custom_definition']}.yml": render_definition(
            source_definition,
            str(target["custom_definition"]),
            str(target["display_name"]),
            str(target["schema_name"]),
        )
        for source_definition, target in TARGETS.items()
    }


def validate_file(path: Path, expected: str) -> None:
    if not path.is_file():
        raise DefinitionError(f"custom definition is missing: {path.name}")
    stat = path.stat()
    if stat.st_uid != 1000 or stat.st_gid != 1000 or stat.st_mode & 0o777 != 0o644:
        raise DefinitionError(
            f"custom definition ownership or mode drifted: {path.name}"
        )
    if path.read_text(encoding="utf-8") != expected:
        raise DefinitionError(f"custom definition content drifted: {path.name}")


def validate_runtime_schema() -> None:
    resources = api_request("indexer/schema")
    if not isinstance(resources, list):
        raise DefinitionError("Prowlarr returned an invalid schema catalog")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for resource in resources:
        grouped.setdefault(definition_name(resource), []).append(resource)

    for source_definition, target in TARGETS.items():
        custom_definition = str(target["custom_definition"])
        display_name = str(target["display_name"])
        matches = grouped.get(custom_definition, [])
        if len(matches) != 1:
            raise DefinitionError(
                f"Prowlarr loaded {len(matches)} schemas for {custom_definition}"
            )
        if matches[0].get("description") != (
            f"{DESCRIPTION_PREFIX}{display_name}"
        ):
            raise DefinitionError(
                f"Prowlarr did not activate the custom {source_definition} "
                "definition"
            )


def grouped_indexers() -> dict[str, list[dict[str, Any]]]:
    resources = api_request("indexer")
    if not isinstance(resources, list):
        raise DefinitionError("Prowlarr returned an invalid indexer catalog")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for resource in resources:
        grouped.setdefault(definition_name(resource), []).append(resource)
    return grouped


def migrate_configured_indexers() -> None:
    grouped = grouped_indexers()
    for source_definition, target in TARGETS.items():
        custom_definition = str(target["custom_definition"])
        source_rows = grouped.get(source_definition, [])
        custom_rows = grouped.get(custom_definition, [])
        if len(source_rows) > 1 or len(custom_rows) > 1:
            raise DefinitionError(
                f"multiple configured indexers use {source_definition}"
            )
        if source_rows and custom_rows:
            raise DefinitionError(
                f"both bundled and custom {source_definition} indexers exist"
            )
        if not source_rows:
            print(
                f"{target['display_name']} configured indexer already uses "
                f"{custom_definition}"
                if custom_rows
                else f"{target['display_name']} has no configured indexer to migrate"
            )
            continue

        desired = copy.deepcopy(source_rows[0])
        set_field(desired, "definitionFile", custom_definition)
        indexer_id = int(desired["id"])
        api_request(
            f"indexer/{indexer_id}?forceSave=true",
            method="PUT",
            payload=desired,
        )
        print(
            f"Migrated {target['display_name']} indexer {indexer_id} to "
            f"{custom_definition} without a login test"
        )


def validate_configured_indexers() -> None:
    grouped = grouped_indexers()
    for source_definition, target in TARGETS.items():
        custom_definition = str(target["custom_definition"])
        if grouped.get(source_definition):
            raise DefinitionError(
                f"configured indexer still uses bundled {source_definition}"
            )
        if len(grouped.get(custom_definition, [])) > 1:
            raise DefinitionError(
                f"multiple configured indexers use {custom_definition}"
            )


def check() -> None:
    for path, expected in expected_definitions().items():
        validate_file(path, expected)
    validate_runtime_schema()
    validate_configured_indexers()
    print(
        "Prowlarr cross-seed proxy definitions passed: "
        "BTSchool and RailgunPT"
    )


def atomic_write(path: Path, content: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        os.chown(path, 1000, 1000)
        os.chmod(path, 0o644)
        return False
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chown(temporary, 1000, 1000)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return True


def apply() -> None:
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    os.chown(CUSTOM_DIR, 1000, 1000)
    os.chmod(CUSTOM_DIR, 0o755)
    changed = False
    for path, expected in expected_definitions().items():
        changed = atomic_write(path, expected) or changed
    print(f"changed={'true' if changed else 'false'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--migrate", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.apply:
            apply()
        elif arguments.migrate:
            migrate_configured_indexers()
        else:
            check()
    except DefinitionError as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
