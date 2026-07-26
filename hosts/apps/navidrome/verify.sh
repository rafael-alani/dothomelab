#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.watch.digest"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    navidrome
)" || fail "Navidrome container is missing"
[[ "$state" == \
  "running healthy navidrome true true docker.backupgated deluan/navidrome:latest" ]] ||
  fail "Navidrome state, image, project, or WUD policy drifted: $state"

docker inspect navidrome |
  python3 -c '
import json
import sys
item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
expected = {
    "/data": ("/srv/appdata/docker/navidrome/data", True),
    "/music": ("/data/media/music", False),
    "/aurral-flows": ("/srv/appdata/docker/aurral/flows", False),
}
if set(mounts) != set(expected):
    raise SystemExit(f"unexpected Navidrome mounts: {sorted(mounts)}")
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or bool(mount["RW"]) != writable:
        raise SystemExit(f"Navidrome mount drifted: {destination}")
if item["Config"].get("User") != "1000:1000":
    raise SystemExit("Navidrome does not run as UID/GID 1000")
env = dict(value.split("=", 1) for value in item["Config"]["Env"])
if env.get("ND_SCANNER_PURGEMISSING") != "always":
    raise SystemExit("Navidrome missing-file purge policy drifted")
'

curl --fail --silent --show-error http://192.168.0.112:4533/ping >/dev/null ||
  fail "Navidrome direct ping failed"
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/navidrome/data)" == \
  "rpool/appdata/docker" ]] || fail "Navidrome data is not canonical appdata"
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/aurral/flows)" == \
  *"aurral-flows]" ]] || fail "Navidrome flow source is not vault/shared"

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://navidrome.rafael.media/ping
)" || fail "private Navidrome HTTPS route failed"
[[ "$https_status" == "200" ]] ||
  fail "Navidrome HTTPS ping returned HTTP $https_status"

printf 'Navidrome verification passed: health, read-only libraries, private HTTPS, appdata, and WUD policy.\n'
