#!/usr/bin/env bash
set -Eeuo pipefail

readonly expected_image="ghcr.io/cleanuparr/cleanuparr:latest@sha256:9f74fa60bbf84c82b86f69fbef75189dd3e38408f99fd9c1895736185c4620b9"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}}' \
    cleanuparr
)" || fail "Cleanuparr container is missing"
[[ "$state" == "running healthy cleanuparr false $expected_image" ]] ||
  fail "Cleanuparr state, image, project, or WUD policy drifted: $state"

docker inspect cleanuparr |
  python3 -c '
import json
import sys

item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
if set(mounts) != {"/config"}:
    raise SystemExit(f"unexpected Cleanuparr mounts: {sorted(mounts)}")
config = mounts["/config"]
if config["Source"] != "/docker/cleanuparr" or not config["RW"]:
    raise SystemExit("Cleanuparr config mount drifted")
if "servarr-hello_default" not in item["NetworkSettings"]["Networks"]:
    raise SystemExit("Cleanuparr is not on the private Servarr network")
ports = item["HostConfig"]["PortBindings"]
if ports != {"11011/tcp": [{"HostIp": "192.168.0.102", "HostPort": "11011"}]}:
    raise SystemExit(f"Cleanuparr port binding drifted: {ports}")
' || fail "Cleanuparr mount, network, or port policy failed"

[[ "$(findmnt -n -o SOURCE -T /docker/cleanuparr)" == \
  "rpool/appdata/docker" ]] || fail "Cleanuparr is not on canonical appdata"
[[ "$(stat -c '%u:%g %a' /docker/cleanuparr)" == "1000:1000 750" ]] ||
  fail "Cleanuparr appdata ownership or mode drifted"

curl --fail --silent --show-error --output /dev/null \
  http://192.168.0.102:11011/health ||
  fail "Cleanuparr direct health endpoint failed"

version="$(
  docker logs cleanuparr 2>&1 |
    sed -n 's/.*Cleanuparr v\([0-9][0-9.]*\).*/\1/p' |
    tail -n 1
)"
[[ "$version" == "2.10.0" ]] ||
  fail "Cleanuparr runtime version is $version, expected 2.10.0"

printf 'Cleanuparr runtime verification passed: v%s, private CT102 port, canonical appdata, shared Servarr network, and manual-update policy.\n' \
  "$version"
