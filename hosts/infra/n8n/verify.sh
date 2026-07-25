#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-n8n}"
readonly N8N_URL="${N8N_URL:-http://192.168.0.110:5678}"
readonly N8N_HTTPS_URL="${N8N_HTTPS_URL:-https://n8n.rafael.media}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}} {{.Config.User}}' \
    n8n
)" || fail "n8n container is missing"
read -r status health project trigger image user <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "n8n state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "n8n project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "n8n is not enrolled in backup-gated WUD"
[[ "$image" == "docker.n8n.io/n8nio/n8n:latest" ]] ||
  fail "n8n image is $image, expected the upstream latest channel"
[[ "$user" == "1000:1000" ]] ||
  fail "n8n runs as $user, expected 1000:1000"

curl --fail --silent --show-error --output /dev/null "$N8N_URL/healthz" ||
  fail "n8n direct health endpoint failed"
curl --fail --silent --show-error --output /dev/null "$N8N_HTTPS_URL/healthz" ||
  fail "n8n private HTTPS health endpoint failed"

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/n8n)" == "rpool/appdata/docker" ]] ||
  fail "n8n state is not on canonical appdata"
[[ "$(stat -c '%u:%g %a' /srv/appdata/docker/n8n)" == "1000:1000 700" ]] ||
  fail "n8n appdata ownership or mode drifted"

printf 'n8n verification passed: image=%s SQLite=appdata HTTPS=private WUD=backup-gated.\n' \
  "$image"
