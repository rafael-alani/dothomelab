#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="${APPDATA_ROOT:-/srv/appdata/docker/mealie}"
readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-apps-mealie}"
readonly MEALIE_URL="${MEALIE_URL:-http://192.168.0.112:9925}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}}' \
    mealie
)" || fail "Mealie container is missing"
read -r status health project trigger <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "Mealie state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "Mealie project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Mealie is not enrolled in backup-gated WUD"

about="$(curl --fail --silent --show-error "$MEALIE_URL/api/app/about")" ||
  fail "Mealie about endpoint failed"
version="$(
  python3 -c 'import json,sys; print(json.load(sys.stdin).get("version", ""))' \
    <<<"$about"
)"
[[ "$version" == "v3.21.0" ]] ||
  fail "Mealie reports $version, expected v3.21.0"

database="$APPDATA_ROOT/mealie.db"
[[ -s "$database" ]] || fail "Mealie SQLite database is missing"
read -r integrity recipes users < <(
  python3 - "$database" <<'PY'
import sqlite3
import sys

with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    recipes = connection.execute("SELECT count(*) FROM recipes").fetchone()[0]
    users = connection.execute("SELECT count(*) FROM users").fetchone()[0]
print(integrity, recipes, users)
PY
)
[[ "$integrity" == "ok" ]] || fail "Mealie database integrity is $integrity"
[[ "$recipes" -gt 0 && "$users" -gt 0 ]] ||
  fail "Mealie restore counts are recipes=$recipes users=$users"

printf 'Mealie verification passed: version=%s recipes=%s users=%s\n' \
  "$version" "$recipes" "$users"
