#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/srv/appdata/docker/storyteller"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

health="$(
  curl --fail --silent --show-error \
    http://192.168.0.112:8001/api/health
)"
python3 -c '
import json
import sys
if json.load(sys.stdin).get("status") != "healthy":
    raise SystemExit(1)
' <<<"$health" ||
  fail "Storyteller direct health endpoint failed"

for container in storyteller storyteller-reconciler; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}}' \
      "$container"
  )"
  [[ "$state" == "running healthy storyteller" ]] ||
    fail "$container state is $state"
done

storyteller_state="$(
  docker inspect --format \
    '{{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.watch.digest"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}} {{.HostConfig.ReadonlyRootfs}} {{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}' \
    storyteller
)"
read -r watched digest trigger image readonly memory nanocpus <<<"$storyteller_state"
[[ "$watched $digest $trigger" == "true true docker.backupgated" ]] ||
  fail "Storyteller backup-gated WUD labels drifted"
[[ "$image" == "registry.gitlab.com/storyteller-platform/storyteller:latest" ]] ||
  fail "Storyteller image drifted: $image"
version="$(
  docker exec storyteller node -p "require('./package.json').version"
)"
python3 - "$version" <<'PY' ||
import sys

def parts(value: str) -> tuple[int, int, int]:
    core = value.lstrip("v").split("-", 1)[0]
    numbers = core.split(".")
    if len(numbers) != 3:
        raise ValueError(value)
    return tuple(int(number) for number in numbers)

if parts(sys.argv[1]) < (2, 14, 13):
    raise SystemExit(1)
PY
  fail "Storyteller $version is below vulnerability floor 2.14.13"
[[ "$readonly" == "true" && "$memory" == "8589934592" &&
  "$nanocpus" == "3000000000" ]] ||
  fail "Storyteller hardening/resource limits drifted"
[[ "$(docker inspect --format '{{index .Config.Labels "wud.watch"}}' \
  storyteller-reconciler)" == "false" ]] ||
  fail "Storyteller reconciler must not update independently"

docker inspect storyteller |
  python3 -c '
import json
import sys

state = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in state["Mounts"]}
expected = {
    "/storyteller": ("/storyteller", True),
    "/state": ("/srv/appdata/docker/storyteller", True),
    "/config/storyteller.json": (
        "/opt/dothomelab/hosts/apps/storyteller/config.json",
        False,
    ),
}
for destination, (source, writable) in expected.items():
    mount = mounts.get(destination)
    if not mount:
        raise SystemExit(f"missing mount {destination}")
    if mount["Source"] != source or bool(mount["RW"]) != writable:
        raise SystemExit(f"mount drift at {destination}: {mount}")
'

docker inspect storyteller-reconciler |
  python3 -c '
import json
import sys

state = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in state["Mounts"]}
for destination in ("/sources/ebooks", "/sources/audiobooks", "/storyteller-db"):
    if destination not in mounts or mounts[destination]["RW"]:
        raise SystemExit(f"{destination} is not read-only")
for destination in ("/storyteller", "/state"):
    if destination not in mounts or not mounts[destination]["RW"]:
        raise SystemExit(f"{destination} is not writable")
if state["HostConfig"]["NetworkMode"] != "none":
    raise SystemExit("reconciler network is enabled")
'

[[ "$(findmnt -n -o SOURCE -T /storyteller)" == vault/shared* ]] ||
  fail "narrow Storyteller bind is not backed by vault/shared"
[[ "$(findmnt -n -o OPTIONS -T /data)" == *ro* ]] ||
  fail "broad CT112 /data is not read-only"
[[ "$(findmnt -n -o SOURCE -T "$appdata/database")" == \
  "rpool/appdata/docker" ]] ||
  fail "Storyteller database is not on appdata"
[[ "$(stat -c '%u:%g %a' "$appdata/secrets/secret_key")" == \
  "1000:1000 600" ]] ||
  fail "Storyteller secret file metadata drifted"

for path in /sources/ebooks /sources/audiobooks; do
  if docker exec storyteller-reconciler test -w "$path"; then
    fail "reconciler can write canonical source $path"
  fi
done

database="$appdata/database/storyteller.db"
[[ -s "$database" ]] || fail "Storyteller database is missing"
integrity="$(
  docker exec storyteller-reconciler python -c '
import sqlite3
connection = sqlite3.connect(
    "file:/storyteller-db/storyteller.db?mode=ro", uri=True
)
print(connection.execute("PRAGMA integrity_check").fetchone()[0])
connection.close()
'
)"
[[ "$integrity" == "ok" ]] ||
  fail "Storyteller database integrity is $integrity"

docker exec storyteller-reconciler python /app/reconciler.py status >/dev/null

printf 'Storyteller verification passed: version=%s health, SQLite=%s, mounts, limits, canonical RO, reconciler, secret, and WUD policy\n' \
  "$version" "$integrity"
