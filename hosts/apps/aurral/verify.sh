#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}}' \
    aurral
)" || fail "Aurral container is missing"
[[ "$state" == \
  "running healthy aurral false ghcr.io/lklynet/aurral:2.0.0-test.7@sha256:a2ce2e4ae4767c3fb445728c3af2e972823b874c7813d290a2054b736100bbf6" ]] ||
  fail "Aurral state, image, project, or WUD policy drifted: $state"

docker inspect aurral |
  python3 -c '
import json
import sys
item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
expected = {
    "/config": ("/srv/appdata/docker/aurral/data", True),
    "/aurral-flows": ("/srv/appdata/docker/aurral/flows", True),
    "/data/media/music": ("/data/media/music", False),
    "/slskd-downloads": ("/slskd-downloads", True),
}
if set(mounts) != set(expected):
    raise SystemExit(f"unexpected Aurral mounts: {sorted(mounts)}")
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or bool(mount["RW"]) != writable:
        raise SystemExit(f"Aurral mount drifted: {destination}")
if item["Config"].get("User"):
    raise SystemExit("Aurral entrypoint cannot start as root for v1 migration")
if sorted(item["HostConfig"].get("CapAdd") or []) != [
    "CHOWN", "DAC_OVERRIDE", "SETGID", "SETUID"
]:
    raise SystemExit("Aurral entrypoint capability set drifted")
if any(value.startswith("SOULSEEK_") for value in item["Config"].get("Env", [])):
    raise SystemExit("Aurral still has legacy built-in Soulseek credentials")
if "slskd-droppedneedle" not in item["NetworkSettings"]["Networks"]:
    raise SystemExit("Aurral is not attached to the private slskd network")
'

app_pid="$(docker exec aurral pgrep -o -x node)"
runtime_user="$(docker exec aurral awk '/^Uid:|^Gid:/ {print $2}' "/proc/$app_pid/status" |
  paste -sd: -)"
[[ "$runtime_user" == "1000:1000" ]] ||
  fail "Aurral application PID 1 is not UID/GID 1000: $runtime_user"
runtime_caps="$(docker exec aurral awk '/^CapEff:/ {print $2}' "/proc/$app_pid/status")"
[[ "$runtime_caps" == "0000000000000000" ]] ||
  fail "Aurral application retained effective entrypoint capabilities"

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/aurral/data)" == \
  "rpool/appdata/docker" ]] || fail "Aurral data is not on canonical appdata"
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/aurral/flows)" == \
  *"aurral-flows]" ]] || fail "Aurral flows are not on vault/shared"
[[ "$(findmnt -n -o SOURCE -T /slskd-downloads)" == vault/shared* ]] ||
  fail "Aurral slskd view is not on vault/shared"

python3 -c '
import sqlite3
connection = sqlite3.connect(
    "file:/srv/appdata/docker/aurral/data/aurral.db?mode=ro", uri=True
)
tables = {
    row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = \"table\""
    )
}
if "aurral_history" not in tables:
    raise SystemExit("Aurral durable Activity history table is missing")
'

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

printf 'Aurral verification passed: v2 history, external slskd, runtime UID, least-privilege mounts, private HTTPS, and manual-update policy.\n'
