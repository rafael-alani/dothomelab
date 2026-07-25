#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-snapotter}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:1349}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    snapotter
)" || fail "SnapOtter app container is missing"
read -r status health project trigger image <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "SnapOtter app state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "SnapOtter app project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "SnapOtter app is not enrolled in backup-gated WUD"
[[ "$image" == "snapotter/snapotter:latest" ]] ||
  fail "SnapOtter app image is $image, expected the upstream latest channel"

declare -A expected_images=(
  [snapotter-db]="postgres:17-alpine"
  [snapotter-redis]="redis:8-alpine"
)
for container in "${!expected_images[@]}"; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}}' \
      "$container"
  )" || fail "$container is missing"
  read -r status health project watched image <<<"$state"
  [[ "$status" == "running" && "$health" == "healthy" ]] ||
    fail "$container state is status=$status health=$health"
  [[ "$project" == "$EXPECTED_PROJECT" ]] ||
    fail "$container project is $project, expected $EXPECTED_PROJECT"
  [[ "$watched" == "false" ]] ||
    fail "$container must remain excluded from automatic WUD updates"
  [[ "$image" == "${expected_images[$container]}" ]] ||
    fail "$container image is $image, expected ${expected_images[$container]}"
done

health_json="$(curl --fail --silent --show-error "$APPS_URL/api/v1/health")" ||
  fail "SnapOtter health endpoint failed"
python3 -c '
import json
import sys
payload = json.load(sys.stdin)
if payload.get("status") != "healthy" or not payload.get("version"):
    raise SystemExit(f"unexpected SnapOtter health payload: {payload!r}")
' <<<"$health_json" || fail "SnapOtter health payload is invalid"

[[ "$(docker exec snapotter-redis redis-cli ping)" == "PONG" ]] ||
  fail "SnapOtter Redis did not return PONG"
docker exec snapotter-db psql \
  --dbname=snapotter \
  --username=snapotter \
  --no-align \
  --tuples-only \
  --command="
    SELECT
      current_setting('server_version_num')::int BETWEEN 170000 AND 179999
      AND (SELECT count(*) >= 1 FROM users);
  " |
  grep -qx 't' || fail "SnapOtter PostgreSQL version or seeded user check failed"

for path in \
  /srv/appdata/docker/snapotter/data \
  /srv/appdata/docker/snapotter/postgres \
  /srv/appdata/docker/snapotter/redis; do
  [[ -d "$path" ]] || fail "persistent path is missing: $path"
  [[ "$(findmnt -n -o SOURCE -T "$path")" == "rpool/appdata/docker" ]] ||
    fail "$path is not on canonical appdata"
done

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://snapotter.rafael.media/
)" || fail "private SnapOtter HTTPS route failed"
[[ "$https_status" =~ ^(200|302|401)$ ]] ||
  fail "SnapOtter HTTPS route returned HTTP $https_status"

printf 'SnapOtter verification passed: app, PostgreSQL 17, Redis 8, storage, private HTTPS, and update policy.\n'
