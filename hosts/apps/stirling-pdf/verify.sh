#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-stirling-pdf}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:8084}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    stirling-pdf
)" || fail "Stirling-PDF container is missing"
read -r status health project trigger image <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "Stirling-PDF state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "Stirling-PDF project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Stirling-PDF is not enrolled in backup-gated WUD"
[[ "$image" == "stirlingtools/stirling-pdf:latest" ]] ||
  fail "Stirling-PDF image is $image, expected the upstream latest channel"

status_json="$(curl --fail --silent --show-error "$APPS_URL/api/v1/info/status")" ||
  fail "Stirling-PDF status endpoint failed"
grep -q 'UP' <<<"$status_json" ||
  fail "Stirling-PDF status endpoint does not report UP"

container_env="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' stirling-pdf
)"
grep -qx 'SECURITY_ENABLELOGIN=true' <<<"$container_env" ||
  fail "Stirling-PDF login is not enabled"
grep -qx 'SYSTEM_GOOGLEVISIBILITY=false' <<<"$container_env" ||
  fail "Stirling-PDF search-engine visibility is not disabled"

for path in \
  /srv/appdata/docker/stirling-pdf/configs \
  /srv/appdata/docker/stirling-pdf/custom-files \
  /srv/appdata/docker/stirling-pdf/pipeline \
  /srv/appdata/docker/stirling-pdf/tessdata; do
  [[ -d "$path" ]] || fail "persistent path is missing: $path"
  [[ "$(findmnt -n -o SOURCE -T "$path")" == "rpool/appdata/docker" ]] ||
    fail "$path is not on canonical appdata"
done

database="$(
  find /srv/appdata/docker/stirling-pdf/configs \
    -maxdepth 1 -type f -name 'stirling-pdf-DB-*.mv.db' -print -quit
)"
[[ -n "$database" && -s "$database" ]] ||
  fail "Stirling-PDF persistent account database is missing"

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://pdf.rafael.media/
)" || fail "private Stirling-PDF HTTPS route failed"
[[ "$https_status" =~ ^(200|302|401)$ ]] ||
  fail "Stirling-PDF HTTPS route returned HTTP $https_status"

printf 'Stirling-PDF verification passed: authenticated UI, persistent state, private HTTPS, and backup-gated WUD.\n'
