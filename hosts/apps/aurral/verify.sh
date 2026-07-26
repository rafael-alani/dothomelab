#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.watch.digest"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    aurral
)" || fail "Aurral container is missing"
[[ "$state" == \
  "running healthy aurral true true docker.backupgated ghcr.io/lklynet/aurral:latest" ]] ||
  fail "Aurral state, image, project, or WUD policy drifted: $state"

docker inspect aurral |
  python3 -c '
import json
import sys
item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
expected = {
    "/app/backend/data": ("/srv/appdata/docker/aurral/data", True),
    "/aurral-flows": ("/srv/appdata/docker/aurral/flows", True),
    "/data/media/music": ("/data/media/music", False),
}
if set(mounts) != set(expected):
    raise SystemExit(f"unexpected Aurral mounts: {sorted(mounts)}")
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or bool(mount["RW"]) != writable:
        raise SystemExit(f"Aurral mount drifted: {destination}")
if item["Config"].get("User") != "1000:1000":
    raise SystemExit("Aurral does not run as UID/GID 1000")
'

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/aurral/data)" == \
  "rpool/appdata/docker" ]] || fail "Aurral data is not on canonical appdata"
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/aurral/flows)" == \
  *"aurral-flows]" ]] || fail "Aurral flows are not on vault/shared"

health="$(curl --fail --silent --show-error \
  http://192.168.0.112:3001/api/health/bootstrap)"
python3 -c '
import json
import sys
state = json.loads(sys.argv[1])
if state.get("status") != "ok":
    raise SystemExit("Aurral health is not ok")
if state.get("onboardingRequired") is not False:
    raise SystemExit("Aurral onboarding is incomplete")
if state.get("lidarrConfigured") is not True:
    raise SystemExit("Aurral has no Lidarr integration")
' "$health"

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://aurral.rafael.media/
)" || fail "private Aurral HTTPS route failed"
[[ "$https_status" =~ ^(200|302|401)$ ]] ||
  fail "Aurral HTTPS returned HTTP $https_status"

printf 'Aurral verification passed: health, onboarding, least-privilege mounts, private HTTPS, and WUD policy.\n'
