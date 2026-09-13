#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-media}"
readonly APPS_HOST="${APPS_HOST:-192.168.0.112}"
readonly PROJECT_NETWORK="${PROJECT_NETWORK:-${EXPECTED_PROJECT}_default}"

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

network_endpoints="$(
  docker network inspect --format \
    '{{range .Containers}}{{.Name}}|{{.MacAddress}}{{println}}{{end}}' \
    "$PROJECT_NETWORK"
)" || fail "$PROJECT_NETWORK is missing"
duplicate_macs="$(
  awk -F '|' '
    $2 != "" {
      count[$2]++
      containers[$2] = containers[$2] " " $1
    }
    END {
      for (mac in count) {
        if (count[mac] > 1) {
          print mac ":" containers[mac]
        }
      }
    }
  ' <<<"$network_endpoints"
)"
[[ -z "$duplicate_macs" ]] ||
  fail "$PROJECT_NETWORK has duplicate container MAC addresses: $duplicate_macs"

docker exec jellystat node -e '
  const db = require("/app/backend/db");
  db.pool.query("SELECT 1")
    .then(() => db.pool.end())
    .catch((error) => {
      console.error(error.code || error.message);
      process.exit(1);
    });
' || fail "Jellystat cannot query its PostgreSQL database"

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
