#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-immichframe}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:8080}"
readonly IMMICH_URL="${IMMICH_URL:-http://192.168.0.112:2283}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    immichframe
)" || fail "ImmichFrame container is missing"
read -r status project trigger image <<<"$state"
[[ "$status" == "running" ]] || fail "ImmichFrame is $status"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "ImmichFrame project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "ImmichFrame is not enrolled in backup-gated WUD"
[[ "$image" == "ghcr.io/immichframe/immichframe:latest" ]] ||
  fail "ImmichFrame image is $image, expected the upstream latest channel"

curl --fail --silent --show-error --output /dev/null "$IMMICH_URL/api/server/ping" ||
  fail "Immich dependency endpoint failed"
curl --fail --silent --show-error --output /dev/null "$APPS_URL/" ||
  fail "ImmichFrame endpoint failed"

api_key="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' immichframe |
    sed -n 's/^ApiKey=//p'
)"
[[ -n "$api_key" ]] || fail "ImmichFrame API key is empty"
auth_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --header "x-api-key: $api_key" \
    "$IMMICH_URL/api/albums"
)" || fail "Immich API-key validation request failed"
unset api_key
[[ "$auth_status" == "200" ]] ||
  fail "Immich rejected the configured ImmichFrame album-read scope with HTTP $auth_status"

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/immichframe/config)" == \
  "rpool/appdata/docker" ]] ||
  fail "ImmichFrame config is not on canonical appdata"

printf 'ImmichFrame verification passed: UI, Immich dependency, credential, storage, and WUD policy.\n'
