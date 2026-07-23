#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="${APPDATA_ROOT:-/srv/appdata/docker}"
readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-infra-services}"
readonly INFRA_HOST="${INFRA_HOST:-192.168.0.110}"
readonly REQUIRE_AGENT_HTTP="${REQUIRE_AGENT_HTTP:-true}"
readonly REQUIRE_NO_LEGACY_PROXY="${REQUIRE_NO_LEGACY_PROXY:-true}"
readonly MIN_NPM_PROXY_HOSTS="${MIN_NPM_PROXY_HOSTS:-35}"
readonly MIN_NPM_CERTIFICATES="${MIN_NPM_CERTIFICATES:-6}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

http_check() {
  local name="$1"
  local url="$2"
  local insecure="${3:-false}"
  local accepted_status="${4:-^[23][0-9][0-9]$}"
  local curl_args=(
    --silent
    --show-error
    --output /dev/null
    --write-out '%{http_code}'
    --connect-timeout 5
    --max-time 15
  )

  if [[ "$insecure" == "true" ]]; then
    curl_args+=(--insecure)
  fi

  local status
  status="$(curl "${curl_args[@]}" "$url")" ||
    fail "$name HTTP request failed: $url"
  [[ "$status" =~ $accepted_status ]] ||
    fail "$name returned HTTP $status: $url"
  printf 'OK http %-18s %s\n' "$name" "$status"
}

containers=(
  pihole
  homarr
  nginx-proxy-manager
  cloudflare-ddns
  helloworld
  portainer
  portainer_agent
)

for container in "${containers[@]}"; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{if index .State "Health"}}{{index (index .State "Health") "Status"}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}}' \
      "$container"
  )" || fail "$container is missing"
  read -r status health project trigger <<<"$state"
  [[ "$status" == "running" ]] || fail "$container is $status"
  [[ "$health" == "none" || "$health" == "healthy" ]] ||
    fail "$container health is $health"
  [[ "$project" == "$EXPECTED_PROJECT" ]] ||
    fail "$container belongs to ${project:-no Compose project}, expected $EXPECTED_PROJECT"
  [[ "$trigger" == "docker.backupgated" ]] ||
    fail "$container is not enrolled in the backup-gated WUD trigger"
  printf 'OK container %-19s health=%s project=%s\n' \
    "$container" "$health" "$project"
done

wud_state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    wud
)" || fail "WUD container is missing"
[[ "$wud_state" == "running healthy" ]] || fail "WUD state is $wud_state"
printf 'OK container wud                 health=healthy project=wud\n'

http_check pihole "http://$INFRA_HOST:8080/admin/"
http_check homarr "http://$INFRA_HOST:7575/"
http_check nginx-proxy-manager "http://$INFRA_HOST:81/api/"
http_check helloworld "http://$INFRA_HOST:8888/"
http_check portainer "https://$INFRA_HOST:9443/api/system/status" true
if [[ "$REQUIRE_AGENT_HTTP" == "true" ]]; then
  http_check portainer-agent "https://$INFRA_HOST:9001/ping" true
fi

docker exec nginx-proxy-manager nginx -t >/dev/null ||
  fail "Nginx Proxy Manager configuration is invalid"
printf 'OK config Nginx Proxy Manager\n'

npm_database="$APPDATA_ROOT/infra-nginx-proxy-manager/data/database.sqlite"
[[ -s "$npm_database" ]] || fail "NPM database is missing: $npm_database"
read -r integrity proxy_hosts certificates < <(
  python3 - "$npm_database" <<'PY'
import sqlite3
import sys

with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    proxy_hosts = connection.execute("SELECT count(*) FROM proxy_host").fetchone()[0]
    certificates = connection.execute("SELECT count(*) FROM certificate").fetchone()[0]
print(integrity, proxy_hosts, certificates)
PY
)
[[ "$integrity" == "ok" ]] || fail "NPM database integrity is $integrity"
[[ "$proxy_hosts" -ge "$MIN_NPM_PROXY_HOSTS" ]] ||
  fail "NPM has $proxy_hosts proxy hosts, expected at least $MIN_NPM_PROXY_HOSTS"
[[ "$certificates" -ge "$MIN_NPM_CERTIFICATES" ]] ||
  fail "NPM has $certificates certificates, expected at least $MIN_NPM_CERTIFICATES"
printf 'OK data NPM integrity=%s proxy_hosts=%s certificates=%s\n' \
  "$integrity" "$proxy_hosts" "$certificates"

[[ -s "$APPDATA_ROOT/infra-portainer/portainer.db" ]] ||
  fail "Portainer database is missing from SSD appdata"
[[ "$(findmnt -n -o SOURCE -T "$APPDATA_ROOT")" == "rpool/appdata/docker" ]] ||
  fail "$APPDATA_ROOT is not mounted from rpool/appdata/docker"
printf 'OK storage NPM and Portainer state are on rpool/appdata/docker\n'

if [[ "$REQUIRE_NO_LEGACY_PROXY" == "true" ]]; then
  legacy_count="$(
    docker ps -a \
      --filter label=com.docker.compose.project=proxy \
      --format '{{.ID}}' |
      wc -l
  )"
  [[ "$legacy_count" -eq 0 ]] ||
    fail "$legacy_count container(s) still belong to the legacy proxy project"
fi

printf 'Infra verification passed.\n'
