#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-media}"
readonly APPS_HOST="${APPS_HOST:-192.168.0.112}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

for container in jellyfin seerr jellystat-db jellystat; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}}' \
      "$container"
  )" || fail "$container is missing"
  read -r status health project watched <<<"$state"
  [[ "$status" == "running" ]] || fail "$container is $status"
  [[ "$health" == "none" || "$health" == "healthy" ]] ||
    fail "$container health is $health"
  [[ "$project" == "$EXPECTED_PROJECT" ]] ||
    fail "$container project is $project, expected $EXPECTED_PROJECT"
  if [[ "$container" == "jellystat-db" ]]; then
    [[ "$watched" == "false" ]] || fail "Jellystat PostgreSQL must remain manual"
  else
    [[ "$watched" == "true" ]] || fail "$container is not watched by WUD"
  fi
done

for check in \
  "jellyfin|http://$APPS_HOST:8096/health" \
  "seerr|http://$APPS_HOST:5055/api/v1/settings/public" \
  "jellystat|http://$APPS_HOST:3000/auth/isConfigured"; do
  name="${check%%|*}"
  url="${check#*|}"
  curl --fail --silent --show-error --output /dev/null "$url" ||
    fail "$name endpoint failed: $url"
done

printf 'Apps media verification passed.\n'
