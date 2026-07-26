#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}} {{.Config.User}}' \
    music-metadata
)" || fail "music-metadata container is missing"
[[ "$state" == \
  "running healthy music-metadata false lscr.io/linuxserver/beets:latest@sha256:6692c837f2f080d5111b33ec20035139e339081b83f0c31213faa2738b94fd48 1000:996" ]] ||
  fail "music-metadata runtime or update policy drifted: $state"

docker inspect music-metadata |
  python3 -c '
import json
import sys

item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
expected = {
    "/config": ("/srv/appdata/docker/music-metadata", True),
    "/soularr-state": ("/srv/appdata/docker/soularr", True),
    "/music": ("/music", True),
    "/opt/dothomelab/config.yaml": (
        "/opt/dothomelab/hosts/apps/music-metadata/config.yaml", False
    ),
    "/opt/dothomelab/worker.py": (
        "/opt/dothomelab/hosts/apps/music-metadata/worker.py", False
    ),
}
if set(mounts) != set(expected):
    raise SystemExit(f"unexpected music-metadata mounts: {sorted(mounts)}")
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or bool(mount["RW"]) != writable:
        raise SystemExit(f"music-metadata mount drifted: {destination}")
env = dict(value.split("=", 1) for value in item["Config"]["Env"])
expected_env = {
    "LIDARR_URL": "http://192.168.0.102:8686",
    "MUSIC_METADATA_POLL_SECONDS": "300",
    "MUSIC_METADATA_IMPORT_GRACE_SECONDS": "600",
    "MUSIC_METADATA_BEETS_CONFIG": "/opt/dothomelab/config.yaml",
}
drift = {key: env.get(key) for key, value in expected_env.items()
         if env.get(key) != value}
if drift:
    raise SystemExit(f"music-metadata environment drift: {drift}")
if len(env.get("LIDARR_API_KEY", "")) < 16:
    raise SystemExit("music-metadata Lidarr API key is missing")
if item["HostConfig"].get("ReadonlyRootfs") is not True:
    raise SystemExit("music-metadata root filesystem is not read-only")
'

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/music-metadata)" == \
  "rpool/appdata/docker" ]] || fail "music-metadata appdata is not canonical"
[[ "$(findmnt -n -o SOURCE -T /music)" == vault/shared* ]] ||
  fail "music-metadata music bind is not on vault/shared"

docker exec music-metadata python3 /opt/dothomelab/worker.py check >/dev/null ||
  fail "music-metadata deterministic writer check failed"

printf 'Music metadata verification passed: deterministic Beets writer, exact Lidarr policy, canonical state, narrow RW music, and shared acquisition lock.\n'
