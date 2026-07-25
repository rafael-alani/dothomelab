#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-yt-dlp-web-ui}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:3033}"
readonly downloads="/downloads"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}} {{.Config.User}}' \
    yt-dlp-web-ui
)" || fail "yt-dlp Web UI container is missing"
read -r status health project trigger image user <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "yt-dlp Web UI state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "yt-dlp Web UI project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "yt-dlp Web UI is not enrolled in backup-gated WUD"
[[ "$image" == "ghcr.io/marcopiovanello/yt-dlp-web-ui:latest" ]] ||
  fail "yt-dlp Web UI image is $image, expected the upstream latest channel"
[[ "$user" == "1000:1000" ]] ||
  fail "yt-dlp Web UI runs as $user, expected 1000:1000"

status_code="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "$APPS_URL/"
)" || fail "yt-dlp Web UI endpoint failed"
[[ "$status_code" =~ ^(200|401)$ ]] ||
  fail "yt-dlp Web UI returned HTTP $status_code"

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/yt-dlp-web-ui)" == \
  "rpool/appdata/docker" ]] ||
  fail "yt-dlp Web UI config is not on canonical appdata"
download_source="$(findmnt -n -o SOURCE --target "$downloads")"
[[ "$download_source" == vault/shared* ]] ||
  fail "$downloads is mounted from $download_source, expected vault/shared"

probe="$downloads/.dothomelab-write-probe"
trap 'rm -f "$probe"' EXIT
docker exec yt-dlp-web-ui sh -c \
  'printf "yt-dlp write verification\n" > /downloads/.dothomelab-write-probe' ||
  fail "$downloads is not writable by the container service account"
[[ "$(stat -c '%u:%g' "$probe")" == "1000:1000" ]] ||
  fail "download write probe has the wrong ownership"
rm -f "$probe"
trap - EXIT

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://yt-dlp.rafael.media/
)" || fail "private yt-dlp HTTPS route failed"
[[ "$https_status" =~ ^(200|401)$ ]] ||
  fail "yt-dlp HTTPS route returned HTTP $https_status"

printf 'yt-dlp Web UI verification passed: HTTP=%s HTTPS=%s auth, shared downloads, appdata, and WUD policy.\n' \
  "$status_code" "$https_status"
