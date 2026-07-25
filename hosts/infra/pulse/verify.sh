#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-pulse}"
readonly PULSE_URL="${PULSE_URL:-http://192.168.0.110:7655}"
readonly PULSE_HTTPS_URL="${PULSE_HTTPS_URL:-https://pulse.rafael.media}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    pulse
)" || fail "Pulse container is missing"
read -r status health project trigger image <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "Pulse state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "Pulse project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Pulse is not enrolled in backup-gated WUD"
[[ "$image" == "rcourtman/pulse:latest" ]] ||
  fail "Pulse image is $image, expected the upstream latest channel"

curl --fail --silent --show-error --output /dev/null "$PULSE_URL/api/health" ||
  fail "Pulse direct health endpoint failed"
curl --fail --silent --show-error --output /dev/null "$PULSE_HTTPS_URL/api/health" ||
  fail "Pulse private HTTPS health endpoint failed"

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/pulse)" == "rpool/appdata/docker" ]] ||
  fail "Pulse state is not on canonical appdata"
[[ "$(stat -c '%u:%g %a' /srv/appdata/docker/pulse)" == "1000:1000 700" ]] ||
  fail "Pulse appdata ownership or mode drifted"

printf 'Pulse verification passed: image=%s state=appdata HTTPS=private WUD=backup-gated.\n' \
  "$image"
