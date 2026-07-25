#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-wizarr}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:5690}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    wizarr
)" || fail "Wizarr container is missing"
read -r status project trigger image <<<"$state"
[[ "$status" == "running" ]] || fail "Wizarr is $status"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "Wizarr project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Wizarr is not enrolled in backup-gated WUD"
[[ "$image" == "ghcr.io/wizarrrr/wizarr:latest" ]] ||
  fail "Wizarr image is $image, expected the upstream latest channel"

status_code="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "$APPS_URL/"
)" || fail "Wizarr endpoint failed"
[[ "$status_code" =~ ^(200|302|307)$ ]] ||
  fail "Wizarr returned HTTP $status_code"

database="$(
  find /srv/appdata/docker/wizarr -maxdepth 3 -type f \
    \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) \
    -print -quit
)"
[[ -n "$database" && -s "$database" ]] ||
  fail "Wizarr persistent database is missing"

integrity="$(python3 - "$database" <<'PY'
import sqlite3
import sys

with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    print(connection.execute("PRAGMA integrity_check").fetchone()[0])
PY
)"
[[ "$integrity" == "ok" ]] || fail "Wizarr database integrity is $integrity"
[[ "$(findmnt -n -o SOURCE -T "$database")" == "rpool/appdata/docker" ]] ||
  fail "Wizarr database is not on canonical appdata"

printf 'Wizarr verification passed: HTTP=%s database=%s storage and WUD policy.\n' \
  "$status_code" "$integrity"
