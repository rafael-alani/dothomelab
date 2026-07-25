#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-paperless-gpt}"
readonly PAPERLESS_URL="${PAPERLESS_URL:-http://192.168.0.112:8002}"
readonly PAPERLESS_GPT_URL="${PAPERLESS_GPT_URL:-http://192.168.0.112:8003}"

: "${PAPERLESS_GPT_API_TOKEN:?set PAPERLESS_GPT_API_TOKEN}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}}' \
    paperless-gpt
)" || fail "paperless-gpt is missing"
read -r status health project <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "paperless-gpt state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "paperless-gpt project is $project, expected $EXPECTED_PROJECT"

trigger="$(
  docker inspect --format \
    '{{index .Config.Labels "wud.trigger.include"}}' paperless-gpt
)"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "paperless-gpt is not enrolled in backup-gated WUD"

network="$(
  docker inspect --format \
    '{{if index .NetworkSettings.Networks "dothomelab-paperless"}}present{{end}}' \
    paperless-gpt
)"
[[ "$network" == "present" ]] ||
  fail "paperless-gpt is not attached to dothomelab-paperless"

curl --fail --silent --show-error --output /dev/null \
  --header "Authorization: Token $PAPERLESS_GPT_API_TOKEN" \
  "$PAPERLESS_URL/api/documents/?page_size=1" ||
  fail "Paperless-GPT API token cannot access Paperless-ngx"
curl --fail --silent --show-error --output /dev/null "$PAPERLESS_GPT_URL/" ||
  fail "Paperless-GPT UI failed"

for path in \
  /srv/appdata/docker/paperless/gpt/prompts \
  /srv/appdata/docker/paperless/gpt/config \
  /srv/appdata/docker/paperless/gpt/db; do
  [[ -d "$path" ]] || fail "persistent path is missing: $path"
done

status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://paperless-gpt.rafael.media/
)" || fail "private HTTPS route failed: https://paperless-gpt.rafael.media/"
[[ "$status" == "200" ]] ||
  fail "https://paperless-gpt.rafael.media/ returned HTTP $status"

printf 'Paperless-GPT verification passed: Paperless API access and private HTTPS are healthy.\n'
