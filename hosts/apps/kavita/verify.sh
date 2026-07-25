#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-kavita}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:5000}"
readonly appdata_root="/srv/appdata/docker/kavita"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}} {{.Config.User}}' \
    kavita
)" || fail "Kavita container is missing"
read -r status health project trigger image user <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "Kavita state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "Kavita project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Kavita is not enrolled in backup-gated WUD"
[[ "$image" == "ghcr.io/kareadita/kavita:latest" ]] ||
  fail "Kavita image is $image, expected the upstream latest channel"
[[ "$user" == "1000:1000" ]] ||
  fail "Kavita runs as $user, expected 1000:1000"

status_code="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "$APPS_URL/api/health"
)" || fail "Kavita health endpoint failed"
[[ "$status_code" == "200" ]] || fail "Kavita returned HTTP $status_code"

database="$appdata_root/kavita.db"
[[ -s "$database" ]] || fail "Kavita database is missing or empty"
integrity="$(python3 - "$database" <<'PY'
import sqlite3
import sys

with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    print(connection.execute("PRAGMA integrity_check").fetchone()[0])
PY
)"
[[ "$integrity" == "ok" ]] || fail "Kavita database integrity is $integrity"
[[ "$(findmnt -n -o SOURCE -T "$database")" == "rpool/appdata/docker" ]] ||
  fail "Kavita database is not on canonical appdata"

docker inspect --format '{{json .Mounts}}' kavita |
  python3 -c '
import json
import sys

mounts = {mount["Destination"]: mount for mount in json.load(sys.stdin)}
expected = {
    "/kavita/config": ("/srv/appdata/docker/kavita", True),
    "/books": ("/data/media/books", False),
    "/comics": ("/data/media/comics", False),
    "/manga": ("/data/media/mangas", False),
}
for destination, (source, writable) in expected.items():
    mount = mounts.get(destination)
    if mount is None:
        raise SystemExit(f"missing Kavita mount {destination}")
    if mount.get("Source") != source or bool(mount.get("RW")) != writable:
        raise SystemExit(
            f"Kavita mount drift for {destination}: "
            f"source={mount.get('Source')} rw={mount.get('RW')}"
        )
'

printf 'Kavita verification passed: HTTP=%s database=%s mounts, storage, identity, and WUD policy.\n' \
  "$status_code" "$integrity"
