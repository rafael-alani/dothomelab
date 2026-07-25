#!/usr/bin/env python3
"""Run backup-gated WUD updates sequentially from the infra LXC."""

from __future__ import annotations

import argparse
import json
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

WUD_API = "http://127.0.0.1:3001/api"
TRIGGER_ID = "docker.backupgated"
TRIGGER_PATH = "docker/backupgated"
CERT_DIR = "/etc/dothomelab/wud-docker-api"
WATCHER_ORDER = {"infra": 0, "apps": 1, "servarr": 2}
DOCKER_ENDPOINTS = {
    "infra": [],
    "apps": [
        "--host",
        "tcp://192.168.0.112:2376",
        "--tlsverify",
        "--tlscacert",
        f"{CERT_DIR}/ca.pem",
        "--tlscert",
        f"{CERT_DIR}/client-cert.pem",
        "--tlskey",
        f"{CERT_DIR}/client-key.pem",
    ],
    "servarr": [
        "--host",
        "tcp://192.168.0.102:2376",
        "--tlsverify",
        "--tlscacert",
        f"{CERT_DIR}/ca.pem",
        "--tlscert",
        f"{CERT_DIR}/client-cert.pem",
        "--tlskey",
        f"{CERT_DIR}/client-key.pem",
    ],
}
SERVICE_CHECKS = {
    ("infra", "n8n"): (
        "http://192.168.0.110:5678/healthz",
        {200},
    ),
    ("infra", "pulse"): (
        "http://192.168.0.110:7655/api/health",
        {200},
    ),
    ("infra", "syncthing"): (
        "http://127.0.0.1:8384/rest/noauth/health",
        {200},
    ),
    ("infra", "nginx-proxy-manager"): (
        "http://192.168.0.110:81/api/",
        {200},
    ),
    ("infra", "portainer"): (
        "https://192.168.0.110:9443/api/system/status",
        {200},
    ),
    ("infra", "portainer_agent"): (
        "https://192.168.0.110:9001/ping",
        {200, 204},
    ),
    ("servarr", "portainer"): (
        "https://192.168.0.102:9443/api/system/status",
        {200},
    ),
    ("servarr", "portainer_agent"): (
        "https://192.168.0.102:9001/ping",
        {200, 204},
    ),
    ("servarr", "shelfarr"): (
        "http://192.168.0.102:5056/up",
        {200},
    ),
    ("servarr", "shelfarr-libation"): (
        "http://192.168.0.102:5056/up",
        {200},
    ),
    ("apps", "portainer"): (
        "https://192.168.0.112:9443/api/system/status",
        {200},
    ),
    ("apps", "portainer_agent"): (
        "https://192.168.0.112:9001/ping",
        {200, 204},
    ),
    ("apps", "audiobookshelf"): (
        "http://192.168.0.112:13378/",
        {200},
    ),
    ("apps", "bookorbit"): (
        "http://192.168.0.112:3002/api/v1/health",
        {200},
    ),
    ("apps", "storyteller"): (
        "http://192.168.0.112:8001/api/health",
        {200},
    ),
    ("apps", "immichframe"): (
        "http://192.168.0.112:8080/",
        {200},
    ),
    ("apps", "kavita"): (
        "http://192.168.0.112:5000/api/health",
        {200},
    ),
    ("apps", "droppedneedle"): (
        "http://192.168.0.112:8688/health",
        {200},
    ),
    ("apps", "paperless-ngx"): (
        "http://192.168.0.112:8002/",
        {200, 302},
    ),
    ("apps", "paperless-gpt"): (
        "http://192.168.0.112:8003/",
        {200},
    ),
    ("apps", "snapotter"): (
        "http://192.168.0.112:1349/api/v1/health",
        {200},
    ),
    ("apps", "stirling-pdf"): (
        "http://192.168.0.112:8084/api/v1/info/status",
        {200},
    ),
    ("apps", "wizarr"): (
        "http://192.168.0.112:5690/",
        {200, 302, 307},
    ),
    ("apps", "yt-dlp-web-ui"): (
        "http://192.168.0.112:3033/",
        {200, 401},
    ),
}


def log(message: str) -> None:
    print(
        f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}",
        flush=True,
    )


def api_request(path: str, method: str = "GET", timeout: int = 900) -> Any:
    request = urllib.request.Request(
        f"{WUD_API}{path}",
        data=b"" if method == "POST" else None,
        method=method,
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"WUD {method} {path} returned HTTP {error.code}: {detail}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"WUD {method} {path} failed: {error}") from error
    return json.loads(payload) if payload else None


def docker_inspect(watcher: str, container_name: str) -> dict[str, Any]:
    if watcher not in DOCKER_ENDPOINTS:
        raise RuntimeError(f"Unknown WUD watcher: {watcher}")
    command = [
        "docker",
        *DOCKER_ENDPOINTS[watcher],
        "inspect",
        container_name,
    ]
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    inspected = json.loads(result.stdout)
    if len(inspected) != 1:
        raise RuntimeError(
            f"Expected one {watcher} container named {container_name}"
        )
    return inspected[0]


def storyteller_guard(command_name: str) -> bool:
    """Acquire/release the Apps-side update marker without touching its DB."""
    command = [
        "docker",
        *DOCKER_ENDPOINTS["apps"],
        "exec",
        "storyteller-reconciler",
        "python",
        "/app/reconciler.py",
        command_name,
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    detail = (result.stdout or result.stderr).strip()
    if result.returncode == 75 and command_name in {"busy", "wud-acquire"}:
        log(f"STORYTELLER-BUSY: {detail}")
        return False
    if result.returncode:
        raise RuntimeError(
            f"Storyteller {command_name} failed with exit "
            f"{result.returncode}: {detail}"
        )
    log(f"STORYTELLER-GUARD {command_name}: {detail}")
    return True


def associated_with_trigger(container_id: str) -> bool:
    encoded_id = urllib.parse.quote(container_id, safe="")
    triggers = api_request(f"/containers/{encoded_id}/triggers")
    return any(trigger.get("id") == TRIGGER_ID for trigger in triggers or [])


def wait_for_healthy_replacement(
    watcher: str,
    container_name: str,
    previous_id: str,
    timeout: int = 600,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    running_since: float | None = None
    last_state = "container unavailable"

    while time.monotonic() < deadline:
        try:
            inspected = docker_inspect(watcher, container_name)
        except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError):
            inspected = {}

        if inspected and inspected.get("Id") != previous_id:
            state = inspected.get("State", {})
            health = state.get("Health", {}).get("Status")
            running = bool(state.get("Running"))
            last_state = f"running={running} health={health or 'none'}"

            if running and health == "healthy":
                return inspected
            if running and health is None:
                running_since = running_since or time.monotonic()
                if time.monotonic() - running_since >= 15:
                    return inspected
            else:
                running_since = None

        time.sleep(5)

    raise RuntimeError(
        f"{watcher}/{container_name} did not become a healthy replacement "
        f"within {timeout}s ({last_state})"
    )


def wait_for_service_check(
    watcher: str,
    container_name: str,
    timeout: int = 120,
) -> None:
    check = SERVICE_CHECKS.get((watcher, container_name))
    if check is None:
        return

    url, accepted_statuses = check
    deadline = time.monotonic() + timeout
    last_state = "request not attempted"
    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = ssl.CERT_NONE

    while time.monotonic() < deadline:
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=10,
                context=tls_context,
            ) as response:
                status = response.status
                payload = response.read()
            last_state = f"HTTP {status}"
            if status in accepted_statuses:
                if container_name == "portainer":
                    decoded = json.loads(payload)
                    if not decoded.get("Version"):
                        raise RuntimeError(
                            "Portainer status response has no Version"
                        )
                if container_name == "storyteller":
                    decoded = json.loads(payload)
                    if decoded.get("status") != "healthy":
                        raise RuntimeError(
                            "Storyteller health response is not healthy"
                        )
                log(
                    f"SERVICE-OK {watcher}/{container_name}: "
                    f"{url} returned HTTP {status}"
                )
                return
        except urllib.error.HTTPError as error:
            last_state = f"HTTP {error.code}"
            if error.code in accepted_statuses:
                log(
                    f"SERVICE-OK {watcher}/{container_name}: "
                    f"{url} returned HTTP {error.code}"
                )
                return
        except (
            OSError,
            RuntimeError,
            json.JSONDecodeError,
            urllib.error.URLError,
        ) as error:
            last_state = str(error)
        time.sleep(5)

    raise RuntimeError(
        f"{watcher}/{container_name} failed service check within "
        f"{timeout}s ({last_state})"
    )


def update_container(container: dict[str, Any], dry_run: bool) -> None:
    container_id = str(container["id"])
    container_name = str(container["name"]).removeprefix("/")
    watcher = str(container["watcher"])
    result = container.get("result") or {}
    target = result.get("tag") or result.get("digest") or result

    if not associated_with_trigger(container_id):
        log(f"SKIP {watcher}/{container_name}: {TRIGGER_ID} is not associated")
        return

    current = docker_inspect(watcher, container_name)
    previous_id = str(current["Id"])
    previous_image_id = str(current["Image"])
    configured_image = str(current.get("Config", {}).get("Image", "unknown"))
    log(
        f"CANDIDATE {watcher}/{container_name}: image={configured_image} "
        f"container={previous_id[:12]} image_id={previous_image_id[:19]} "
        f"target={target}"
    )

    if dry_run:
        return

    guarded = False
    if (watcher, container_name) == ("apps", "storyteller"):
        guarded = storyteller_guard("wud-acquire")
        if not guarded:
            log("SKIP apps/storyteller: import or alignment work is active")
            return

    try:
        encoded_id = urllib.parse.quote(container_id, safe="")
        log(f"UPDATING {watcher}/{container_name}")
        api_request(
            f"/containers/{encoded_id}/triggers/{TRIGGER_PATH}",
            method="POST",
        )
        replacement = wait_for_healthy_replacement(
            watcher,
            container_name,
            previous_id,
        )
        wait_for_service_check(watcher, container_name)
        log(
            f"HEALTHY {watcher}/{container_name}: "
            f"container={str(replacement['Id'])[:12]} "
            f"image_id={str(replacement['Image'])[:19]}"
        )
    finally:
        if guarded:
            storyteller_guard("wud-release")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="scan and report eligible updates without invoking WUD triggers",
    )
    parser.add_argument(
        "--check-storyteller-busy",
        action="store_true",
        help="report only whether Storyteller import/alignment work is active",
    )
    args = parser.parse_args()

    if args.check_storyteller_busy:
        return 0 if storyteller_guard("busy") else 75

    log("Requesting a fresh WUD scan across all configured Docker hosts")
    api_request("/containers/watch", method="POST")
    containers = api_request("/containers")
    if args.dry_run:
        discovered = sorted(
            containers or [],
            key=lambda item: (
                WATCHER_ORDER.get(str(item.get("watcher")), 99),
                str(item.get("name")),
            ),
        )
        associated = 0
        for container in discovered:
            watcher = str(container.get("watcher"))
            name = str(container.get("name")).removeprefix("/")
            container_id = str(container.get("id"))
            if associated_with_trigger(container_id):
                associated += 1
                log(f"DISCOVERED {watcher}/{name}: trigger={TRIGGER_ID}")
            else:
                log(f"DISCOVERED {watcher}/{name}: trigger=none")
        log(
            f"Dry-run discovery found {len(discovered)} watched "
            f"container(s), {associated} associated with {TRIGGER_ID}"
        )
    candidates = [
        container
        for container in containers or []
        if container.get("updateAvailable") is True
    ]
    candidates.sort(
        key=lambda item: (
            WATCHER_ORDER.get(str(item.get("watcher")), 99),
            str(item.get("name")),
        )
    )

    if not candidates:
        log("No eligible WUD updates are available")
        return 0

    log(f"Found {len(candidates)} update candidate(s)")
    for container in candidates:
        update_container(container, args.dry_run)
    log("WUD update run completed successfully")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        log(f"ERROR: {error}")
        raise SystemExit(1)
