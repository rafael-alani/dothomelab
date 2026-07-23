#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="${APPDATA_ROOT:-/docker}"
readonly EXPECTED_PROJECT="${EXPECTED_PROJECT-servarr-hello}"
readonly PORTAINER_DATA_ROOT="${PORTAINER_DATA_ROOT:-$APPDATA_ROOT/servarr-portainer}"
readonly REQUIRE_SHARED_DATA="${REQUIRE_SHARED_DATA:-true}"
readonly REQUIRE_AGENT_HTTP="${REQUIRE_AGENT_HTTP:-true}"
readonly SERVARR_HOST="${SERVARR_HOST:-192.168.0.102}"

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
  printf 'OK http %-16s %s\n' "$name" "$status"
}

database_count() {
  local name="$1"
  local path="$2"
  local table="$3"

  [[ -s "$path" ]] || fail "$name database is missing: $path"
  local count
  count="$(
    python3 - "$path" "$table" <<'PY'
import sqlite3
import sys

path, table = sys.argv[1:]
if not table.replace("_", "").isalnum():
    raise SystemExit("unsafe table name")
with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=15) as connection:
    print(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
PY
  )"
  [[ "$count" =~ ^[0-9]+$ ]] || fail "$name returned an invalid record count"
  printf 'OK data %-16s %s records\n' "$name" "$count"
}

containers=(
  gluetun
  qbittorrent
  nzbget
  prowlarr
  sonarr
  radarr
  lidarr
  readarr
  bazarr
  flaresolverr
  deunhealth
  portainer
  portainer_agent
)

for container in "${containers[@]}"; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}}' \
      "$container"
  )" || fail "$container is missing"
  read -r status health project <<<"$state"
  [[ "$status" == "running" ]] || fail "$container is $status"
  [[ "$health" == "none" || "$health" == "healthy" ]] ||
    fail "$container health is $health"
  if [[ -n "$EXPECTED_PROJECT" ]]; then
    [[ "$project" == "$EXPECTED_PROJECT" ]] ||
      fail "$container belongs to ${project:-no Compose project}, expected $EXPECTED_PROJECT"
  fi
  printf 'OK container %-11s running health=%s project=%s\n' \
    "$container" "$health" "$project"
done

docker exec gluetun /gluetun-entrypoint healthcheck >/dev/null ||
  fail "Gluetun native health check failed"
printf 'OK vpn Gluetun native health check\n'

http_check qbittorrent "http://$SERVARR_HOST:8080/"
http_check nzbget "http://$SERVARR_HOST:6789/" false '^[23][0-9][0-9]$|^401$'
http_check prowlarr "http://$SERVARR_HOST:9696/ping"
http_check sonarr "http://$SERVARR_HOST:8989/ping"
http_check radarr "http://$SERVARR_HOST:7878/ping"
http_check lidarr "http://$SERVARR_HOST:8686/ping"
http_check readarr "http://$SERVARR_HOST:8787/ping"
http_check bazarr "http://$SERVARR_HOST:6767/"
http_check flaresolverr "http://$SERVARR_HOST:8191/"
http_check portainer "https://$SERVARR_HOST:9443/api/system/status" true
if [[ "$REQUIRE_AGENT_HTTP" == "true" ]]; then
  http_check portainer-agent "https://$SERVARR_HOST:9001/ping" true
else
  printf 'SKIP http portainer-agent (legacy agent timed out without a client)\n'
fi

database_count prowlarr "$APPDATA_ROOT/prowlarr/prowlarr.db" Indexers
database_count sonarr "$APPDATA_ROOT/sonarr/sonarr.db" Series
database_count radarr "$APPDATA_ROOT/radarr/radarr.db" Movies
database_count lidarr "$APPDATA_ROOT/lidarr/lidarr.db" Artists
database_count readarr "$APPDATA_ROOT/readarr/readarr.db" Authors

torrent_count="$(
  find "$APPDATA_ROOT/qbittorrent/qBittorrent/BT_backup" \
    -maxdepth 1 -type f -name '*.torrent' -print | wc -l
)"
[[ "$torrent_count" -gt 0 ]] || fail "qBittorrent has no persisted torrent state"
printf 'OK data %-16s %s torrent records\n' qbittorrent "$torrent_count"

[[ -s "$APPDATA_ROOT/nzbget/nzbget.conf" ]] ||
  fail "NZBGet configuration is missing"
[[ -s "$PORTAINER_DATA_ROOT/portainer.db" ]] ||
  fail "Portainer database is missing from SSD appdata"
printf 'OK data NZBGet and Portainer configuration present\n'

if [[ "$REQUIRE_SHARED_DATA" == "true" ]]; then
  [[ "$(findmnt -n -o SOURCE -T /data)" == "vault/shared" ]] ||
    fail "/data is not mounted from vault/shared"
  test -r /data/media || fail "/data/media is not readable"
  test -w /data/torrents || fail "/data/torrents is not writable"
  printf 'OK storage /data maps vault/shared; media readable; torrents writable\n'
fi

printf 'Servarr verification passed.\n'
