#!/usr/bin/env python3
"""Reconcile exact Pi-hole local DNS records used by managed private routes."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import tomllib
from pathlib import Path

PIHOLE_CONFIG = Path("/srv/appdata/docker/pihole/etc-pihole/pihole.toml")
MANAGED_RECORDS = {
    "aurral.rafael.media": "192.168.0.110",
    "bookorbit.rafael.media": "192.168.0.110",
    "cleanuparr.rafael.media": "192.168.0.110",
    "navidrome.rafael.media": "192.168.0.110",
    "pinepods.rafael.media": "192.168.0.110",
    "shelfarr.rafael.media": "192.168.0.110",
    "storyteller.rafael.media": "192.168.0.110",
    "syncthing.rafael.media": "192.168.0.110",
}
RETIRED_MANAGED_NAMES = {
    "droppedneedle.rafael.media",
}


def load_hosts() -> list[str]:
    with PIHOLE_CONFIG.open("rb") as handle:
        config = tomllib.load(handle)
    hosts = config.get("dns", {}).get("hosts", [])
    if not isinstance(hosts, list) or not all(isinstance(item, str) for item in hosts):
        raise RuntimeError("Pi-hole dns.hosts is not an array of strings")
    return hosts


def wait_for_pihole() -> None:
    for _ in range(120):
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                "pihole",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip() == "healthy":
            if PIHOLE_CONFIG.is_file():
                return
        time.sleep(1)
    raise RuntimeError("Pi-hole did not become healthy with a persistent config")


def reconcile_hosts(hosts: list[str]) -> list[str]:
    managed_names = set(MANAGED_RECORDS) | RETIRED_MANAGED_NAMES
    retained: list[str] = []
    seen: set[str] = set()
    for record in hosts:
        parts = record.split()
        hostname = parts[1].rstrip(".").lower() if len(parts) == 2 else ""
        if hostname in managed_names or record in seen:
            continue
        retained.append(record)
        seen.add(record)
    retained.extend(f"{address} {hostname}" for hostname, address in MANAGED_RECORDS.items())
    return retained


def verify(hosts: list[str]) -> None:
    for hostname, address in MANAGED_RECORDS.items():
        desired = f"{address} {hostname}"
        if hosts.count(desired) != 1:
            raise RuntimeError(f"Pi-hole exact local DNS record is missing: {hostname}")
    for hostname in RETIRED_MANAGED_NAMES:
        if any(
            len(parts := record.split()) == 2
            and parts[1].rstrip(".").lower() == hostname
            for record in hosts
        ):
            raise RuntimeError(f"retired Pi-hole record is still present: {hostname}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify managed records without changing Pi-hole",
    )
    args = parser.parse_args()

    wait_for_pihole()
    current = load_hosts()
    desired = reconcile_hosts(current)
    if args.check:
        verify(current)
        print("Pi-hole managed local DNS records are present")
        return 0

    if current != desired:
        subprocess.run(
            [
                "docker",
                "exec",
                "pihole",
                "pihole-FTL",
                "--config",
                "dns.hosts",
                json.dumps(desired, separators=(",", ":")),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "exec", "pihole", "pihole", "reloaddns"],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    verify(load_hosts())
    print("Pi-hole managed local DNS records reconciled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
