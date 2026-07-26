#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.watch.digest"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    soularr
)" || fail "Soularr container is missing"
[[ "$state" == \
  "running healthy soularr true true docker.backupgated mrusse08/soularr:latest" ]] ||
  fail "Soularr state, image, project, or WUD policy drifted: $state"

docker inspect soularr |
  python3 -c '
import json
import sys
item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
expected = {
    "/data": ("/docker/soularr", True),
    "/downloads": ("/data/media/slskd", True),
    "/opt/dothomelab/guarded-runner.py": (
        "/opt/dothomelab/hosts/servarr/soularr/guarded-runner.py",
        False,
    ),
}
if set(mounts) != set(expected):
    raise SystemExit(f"unexpected Soularr mounts: {sorted(mounts)}")
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or bool(mount["RW"]) != writable:
        raise SystemExit(f"Soularr mount drifted: {destination}")
if item["Config"].get("User") != "1000:1000":
    raise SystemExit("Soularr does not run as UID/GID 1000")
if item["HostConfig"].get("PortBindings"):
    raise SystemExit("Soularr must not publish its unauthenticated UI")
'

[[ "$(findmnt -n -o SOURCE -T /docker/soularr)" == \
  "rpool/appdata/docker" ]] || fail "Soularr data is not canonical appdata"
[[ "$(findmnt -n -o SOURCE -T /data/media/slskd)" == vault/shared* ]] ||
  fail "Soularr downloads are not on vault/shared"
[[ -s /docker/soularr/config.ini ]] ||
  fail "Soularr rendered config is missing"

python3 -c '
import json
import sqlite3

connection = sqlite3.connect(
    "file:/docker/lidarr/lidarr.db?mode=ro", uri=True
)
rows = connection.execute(
    "SELECT Settings FROM DownloadClients WHERE Implementation = ?",
    ("QBittorrent",),
).fetchall()
if len(rows) != 1:
    raise SystemExit(
        f"expected one Lidarr qBittorrent client, found {len(rows)}"
    )
settings = json.loads(rows[0][0])
if settings.get("host") != "gluetun":
    raise SystemExit(
        "Lidarr qBittorrent client does not use stable Compose DNS"
    )
'

python3 -c '
import configparser
config = configparser.ConfigParser()
config.read("/docker/soularr/config.ini")
expected = {
    ("Lidarr", "host_url"): "http://192.168.0.102:8686",
    ("Lidarr", "download_dir"): "/data/media/slskd/complete",
    ("Slskd", "host_url"): "http://192.168.0.112:5030",
    ("Slskd", "download_dir"): "/downloads/complete",
}
for (section, key), value in expected.items():
    if config.get(section, key) != value:
        raise SystemExit(f"Soularr config drifted: {section}.{key}")
for section in ("Lidarr", "Slskd"):
    if len(config.get(section, "api_key")) < 16:
        raise SystemExit(f"Soularr {section} API key is missing")
'

printf 'Soularr verification passed: private UI, CT102 appdata, qBittorrent DNS, shared path mapping, guarded runner, and WUD policy.\n'
