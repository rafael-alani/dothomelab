#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-bar-assistant}"
readonly FRONTEND_URL="${FRONTEND_URL:-http://192.168.0.112:8200}"
readonly API_URL="${API_URL:-http://192.168.0.112:8201}"
readonly SEARCH_URL="${SEARCH_URL:-http://192.168.0.112:8202}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

declare -A expected_images=(
  [bar-assistant]="barassistant/server:v5"
  [bar-assistant-meilisearch]="getmeili/meilisearch:v1.15"
  [bar-assistant-redis]="redis:8-alpine"
  [bar-assistant-salt-rim]="barassistant/salt-rim:v4"
)

for container in "${!expected_images[@]}"; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}}' \
      "$container"
  )" || fail "$container is missing"
  read -r status health project watched image <<<"$state"
  [[ "$status" == "running" ]] || fail "$container is $status"
  [[ "$health" == "healthy" || "$health" == "none" ]] ||
    fail "$container health is $health"
  [[ "$project" == "$EXPECTED_PROJECT" ]] ||
    fail "$container project is $project, expected $EXPECTED_PROJECT"
  [[ "$watched" == "false" ]] ||
    fail "$container must remain excluded from automatic WUD updates"
  [[ "$image" == "${expected_images[$container]}" ]] ||
    fail "$container image is $image, expected ${expected_images[$container]}"
done

curl --fail --silent --show-error --output /dev/null "$FRONTEND_URL/" ||
  fail "Salt Rim frontend failed"
curl --fail --silent --show-error --output /dev/null \
  "$API_URL/api/server/version" ||
  fail "Bar Assistant API version endpoint failed"
curl --fail --silent --show-error --output /dev/null "$SEARCH_URL/health" ||
  fail "Meilisearch health endpoint failed"
[[ "$(docker exec bar-assistant-redis redis-cli ping)" == "PONG" ]] ||
  fail "Bar Assistant Redis did not return PONG"

for path in \
  /srv/appdata/docker/bar-assistant/data \
  /srv/appdata/docker/bar-assistant/meilisearch \
  /srv/appdata/docker/bar-assistant/redis; do
  [[ -d "$path" ]] || fail "persistent path is missing: $path"
  [[ "$(findmnt -n -o SOURCE -T "$path")" == "rpool/appdata/docker" ]] ||
    fail "$path is not on canonical appdata"
done

database="$(
  find /srv/appdata/docker/bar-assistant/data -type f \
    \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) \
    -print -quit
)"
[[ -n "$database" && -s "$database" ]] ||
  fail "Bar Assistant persistent SQLite database is missing"
integrity="$(python3 - "$database" <<'PY'
import sqlite3
import sys

with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    print(connection.execute("PRAGMA integrity_check").fetchone()[0])
PY
)"
[[ "$integrity" == "ok" ]] ||
  fail "Bar Assistant database integrity is $integrity"

for url in \
  https://bar.rafael.media/ \
  https://bar-api.rafael.media/api/server/version \
  https://bar-search.rafael.media/health; do
  curl --fail --silent --show-error --output /dev/null "$url" ||
    fail "private HTTPS route failed: $url"
done

printf 'Bar Assistant verification passed: frontend, API, search, Redis, SQLite, storage, and manual-update policy.\n'
