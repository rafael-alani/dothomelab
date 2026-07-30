#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="${APPDATA_ROOT:-/docker}"
readonly EXPECTED_PROJECT="${EXPECTED_PROJECT-servarr-hello}"
readonly PORTAINER_DATA_ROOT="${PORTAINER_DATA_ROOT:-$APPDATA_ROOT/servarr-portainer}"
readonly REQUIRE_SHARED_DATA="${REQUIRE_SHARED_DATA:-true}"
readonly REQUIRE_AGENT_HTTP="${REQUIRE_AGENT_HTTP:-true}"
readonly SERVARR_HOST="${SERVARR_HOST:-192.168.0.102}"
readonly EXPECTED_TORRENT_PORT="${EXPECTED_TORRENT_PORT:-52123}"

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

docker inspect gluetun qbittorrent nzbget prowlarr |
  python3 -c '
import json
import sys

expected = sys.argv[1]
gluetun, qbittorrent, nzbget, prowlarr = json.load(sys.stdin)
gluetun_id = gluetun["Id"]
for name, consumer in (
    ("qBittorrent", qbittorrent),
    ("NZBGet", nzbget),
    ("Prowlarr", prowlarr),
):
    if consumer["HostConfig"]["NetworkMode"] != f"container:{gluetun_id}":
        raise SystemExit(f"{name} does not share Gluetun network namespace")
    if consumer["HostConfig"].get("PortBindings"):
        raise SystemExit(f"{name} unexpectedly publishes a direct host port")
gluetun_env = dict(
    item.split("=", 1) for item in gluetun["Config"]["Env"] if "=" in item
)
if gluetun_env.get("VPN_PORT_FORWARDING", "off") != "off":
    raise SystemExit("Gluetun port forwarding requires a NAT-PMP WireGuard key")
if gluetun_env.get("VPN_PORT_FORWARDING_UP_COMMAND"):
    raise SystemExit("stale Gluetun forwarded-port up command is present")
if gluetun_env.get("VPN_PORT_FORWARDING_DOWN_COMMAND"):
    raise SystemExit("stale Gluetun forwarded-port down command is present")
bindings = gluetun["HostConfig"].get("PortBindings") or {}
if "6881/tcp" in bindings or "6881/udp" in bindings:
    raise SystemExit("obsolete qBittorrent LAN port 6881 is still published")
if f"{expected}/tcp" in bindings or f"{expected}/udp" in bindings:
    raise SystemExit("qBittorrent VPN-only port is unexpectedly published on LAN")
qbittorrent_env = dict(
    item.split("=", 1) for item in qbittorrent["Config"]["Env"] if "=" in item
)
if qbittorrent_env.get("TORRENTING_PORT") != expected:
    raise SystemExit("qBittorrent does not declare the allowed tracker port")
' "$EXPECTED_TORRENT_PORT"
printf 'OK vpn qBittorrent, NZBGet, and Prowlarr share Gluetun namespace\n'

docker exec sonarr curl \
  --fail \
  --silent \
  http://gluetun:8080/api/v2/app/preferences |
  python3 -c '
import json
import sys

expected = int(sys.argv[1])
preferences = json.load(sys.stdin)
if preferences.get("listen_port") != expected:
    raise SystemExit("qBittorrent does not use the allowed tracker port")
if preferences.get("current_network_interface") != "tun0":
    raise SystemExit("qBittorrent is not bound to the VPN interface")
if preferences.get("random_port") is not False:
    raise SystemExit("qBittorrent random port selection is enabled")
if preferences.get("upnp") is not False:
    raise SystemExit("qBittorrent UPnP is enabled behind Gluetun")
if preferences.get("bypass_local_auth") is not False:
    raise SystemExit("qBittorrent localhost authentication is disabled")
' "$EXPECTED_TORRENT_PORT" ||
  fail "qBittorrent tracker-port preferences drifted"
printf 'OK vpn qBittorrent uses allowed port %s on tun0\n' \
  "$EXPECTED_TORRENT_PORT"

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

"$(dirname -- "${BASH_SOURCE[0]}")/reconcile-prowlarr-indexers.py" --check

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

  docker inspect nzbget |
    python3 -c '
import json
import sys
mounts = {item["Destination"]: item for item in json.load(sys.stdin)[0]["Mounts"]}
download = mounts.get("/downloads")
if not download or download["Source"] != "/data/usernet" or not download["RW"]:
    raise SystemExit("NZBGet /downloads is not the persistent /data/usernet bind")
'
  printf 'OK storage NZBGet downloads persist under /data/usernet\n'
fi

printf 'Servarr verification passed.\n'
