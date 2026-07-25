#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="${APPDATA_ROOT:-/srv/appdata/docker}"
readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-infra-services}"
readonly INFRA_HOST="${INFRA_HOST:-192.168.0.110}"
readonly REQUIRE_AGENT_HTTP="${REQUIRE_AGENT_HTTP:-true}"
readonly REQUIRE_NO_LEGACY_PROXY="${REQUIRE_NO_LEGACY_PROXY:-true}"
readonly MIN_NPM_PROXY_HOSTS="${MIN_NPM_PROXY_HOSTS:-50}"
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

read -r paperless_route paperless_gpt_route prometheus_route loki_route \
  immichframe_route wizarr_route bar_route bar_api_route \
  bar_search_route ytdlp_route snapotter_route stirling_route \
  slskd_route droppedneedle_route audiobookshelf_route kavita_route \
  n8n_route pulse_route stream_route join_stream_route < <(
  python3 - "$npm_database" <<'PY'
import sqlite3
import sys

expected = {
    '["paperless.rafael.media"]': ("192.168.0.112", 8002),
    '["paperless-gpt.rafael.media"]': ("192.168.0.112", 8003),
    '["prometheus.rafael.media"]': ("192.168.0.112", 9090),
    '["loki.rafael.media"]': ("192.168.0.112", 3100),
    '["immichframe.rafael.media"]': ("192.168.0.112", 8080),
    '["wizarr.rafael.media"]': ("192.168.0.112", 5690),
    '["bar.rafael.media"]': ("192.168.0.112", 8200),
    '["bar-api.rafael.media"]': ("192.168.0.112", 8201),
    '["bar-search.rafael.media"]': ("192.168.0.112", 8202),
    '["yt-dlp.rafael.media"]': ("192.168.0.112", 3033),
    '["snapotter.rafael.media"]': ("192.168.0.112", 1349),
    '["pdf.rafael.media"]': ("192.168.0.112", 8084),
    '["slskd.rafael.media"]': ("192.168.0.112", 5030),
    '["droppedneedle.rafael.media"]': ("192.168.0.112", 8688),
    '["audiobookshelf.rafael.media"]': ("192.168.0.112", 13378),
    '["kavita.rafael.media"]': ("192.168.0.112", 5000),
    '["n8n.rafael.media"]': ("192.168.0.110", 5678),
    '["pulse.rafael.media"]': ("192.168.0.110", 7655),
}
found = {}
public_found = {}
with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    for domain, host, port, enabled, deleted, advanced in connection.execute(
        """
        SELECT domain_names, forward_host, forward_port, enabled, is_deleted,
               advanced_config
        FROM proxy_host
        WHERE domain_names IN (
          '["paperless.rafael.media"]',
          '["paperless-gpt.rafael.media"]',
          '["prometheus.rafael.media"]',
          '["loki.rafael.media"]',
          '["immichframe.rafael.media"]',
          '["wizarr.rafael.media"]',
          '["bar.rafael.media"]',
          '["bar-api.rafael.media"]',
          '["bar-search.rafael.media"]',
          '["yt-dlp.rafael.media"]',
          '["snapotter.rafael.media"]',
          '["pdf.rafael.media"]',
          '["slskd.rafael.media"]',
          '["droppedneedle.rafael.media"]',
          '["audiobookshelf.rafael.media"]',
          '["kavita.rafael.media"]',
          '["n8n.rafael.media"]',
          '["pulse.rafael.media"]'
        )
        """
    ):
        found[domain] = (
            host,
            port,
            enabled,
            deleted,
            "allow 192.168.0.0/24;" in advanced,
            "allow 100.64.0.0/10;" in advanced,
            "deny all;" in advanced,
        )
    for (
        domain,
        host,
        port,
        enabled,
        deleted,
        access_list,
        ssl_forced,
        certificate_id,
        websockets,
        advanced,
    ) in connection.execute(
        """
        SELECT domain_names, forward_host, forward_port, enabled, is_deleted,
               access_list_id, ssl_forced, certificate_id,
               allow_websocket_upgrade, advanced_config
        FROM proxy_host
        WHERE domain_names IN (
          '["stream.rafael.ink"]',
          '["join-stream.rafael.ink"]'
        )
        """
    ):
        public_found[domain] = (
            host,
            port,
            enabled,
            deleted,
            access_list,
            ssl_forced,
            certificate_id > 0,
            websockets,
            "allow 192.168.0.0/24;" in advanced,
            "allow 100.64.0.0/10;" in advanced,
            "deny all;" in advanced,
        )

results = []
for domain, (host, port) in expected.items():
    results.append(
        int(
            found.get(domain)
            == (host, port, 1, 0, True, True, True)
        )
    )
for domain, host, port in (
    ('["stream.rafael.ink"]', "192.168.0.112", 8096),
    ('["join-stream.rafael.ink"]', "192.168.0.112", 5690),
):
    results.append(
        int(
            public_found.get(domain)
            == (host, port, 1, 0, 0, 1, True, 1, False, False, False)
        )
    )
print(*results)
PY
)
[[ "$paperless_route" == "1" && "$paperless_gpt_route" == "1" &&
  "$prometheus_route" == "1" && "$loki_route" == "1" &&
  "$immichframe_route" == "1" && "$wizarr_route" == "1" &&
  "$bar_route" == "1" && "$bar_api_route" == "1" &&
  "$bar_search_route" == "1" && "$ytdlp_route" == "1" &&
  "$snapotter_route" == "1" && "$stirling_route" == "1" &&
  "$slskd_route" == "1" && "$droppedneedle_route" == "1" &&
  "$audiobookshelf_route" == "1" && "$kavita_route" == "1" &&
  "$n8n_route" == "1" && "$pulse_route" == "1" &&
  "$stream_route" == "1" && "$join_stream_route" == "1" ]] ||
  fail "managed NPM routes are absent, have the wrong exposure, or target the wrong backend"
printf 'OK routes all eighteen managed endpoints are private to LAN/Tailscale\n'
printf 'OK routes stream and join-stream are public with TLS and authenticated applications\n'

homarr_database="$APPDATA_ROOT/homarr/db/db.sqlite"
[[ -s "$homarr_database" ]] || fail "Homarr database is missing"
read -r homarr_integrity homarr_apps homarr_items homarr_layouts \
  expected_layouts homarr_reader_apps < <(
  python3 - "$homarr_database" <<'PY'
import sqlite3
import sys

app_ids = (
    "dhlpaperlessngxapp000001",
    "dhlpaperlessgptapp000001",
    "dhlprometheusapp000001",
    "dhllokiapp000000000001",
    "dhlimmichframeapp0000001",
    "dhlwizarrapp000000000001",
    "dhlbarassistantapp000001",
    "dhlytdlpwebuiapp00000010",
    "dhlsnapotterapp000000001",
    "dhlstirlingpdfapp0000001",
    "dhlslskdapp0000000000001",
    "dhldroppedneedleapp00001",
    "dhlaudiobookshelfapp0001",
    "dhlkavitaapp000000000001",
    "dhln8napp000000000000001",
    "dhlpulseapp000000000001",
)
item_ids = (
    "dhlpaperlessngxitemdash1",
    "dhlpaperlessgptitemdash1",
    "dhlpaperlessngxitemadm01",
    "dhlpaperlessgptitemadm01",
    "dhlpaperlessngxitemdef01",
    "dhlpaperlessgptitemdef01",
    "dhlprometheusitemdash1",
    "dhllokiitemdashboard001",
    "dhlprometheusitemadm01",
    "dhllokiitemadmin000001",
    "dhlprometheusitemdef01",
    "dhllokiitemdefault0001",
    "dhlimmichframeitemdash01",
    "dhlwizarritemdashboard01",
    "dhlimmichframeitemadm001",
    "dhlwizarritemadmin000001",
    "dhlimmichframeitemdef001",
    "dhlwizarritemdefault0001",
    "dhlbarassistantdash00001",
    "dhlbarassistantadmin0001",
    "dhlbarassistantdef000010",
    "dhlytdlpwebuidash0000010",
    "dhlytdlpwebuiadmin000010",
    "dhlytdlpwebuidef00000100",
    "dhlsnapotteritemdash0001",
    "dhlsnapotteritemadmin001",
    "dhlsnapotteritemdef00001",
    "dhlstirlingpdfitemdash01",
    "dhlstirlingpdfitemadmin1",
    "dhlstirlingpdfitemdef001",
    "dhlslskditemdashboard001",
    "dhlslskditemadmin0000001",
    "dhlslskditemdefault00001",
    "dhldroppedneedledash0001",
    "dhldroppedneedleadmin001",
    "dhldroppedneedledef00001",
    "dhlaudiobookitemdash0001",
    "dhlaudiobookitemadmin001",
    "dhlaudiobookitemdefault1",
    "dhlkavitaitemdash0000001",
    "dhlkavitaitemadmin000001",
    "dhlkavitaitemdefault0001",
    "dhln8nitemdashboard00001",
    "dhln8nitemadmin00000001",
    "dhln8nitemdefault0000001",
    "dhlpulseitemdashboard001",
    "dhlpulseitemadmin0000001",
    "dhlpulseitemdefault00001",
)
with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    apps = connection.execute(
        f"SELECT count(*) FROM app WHERE id IN ({','.join('?' for _ in app_ids)})",
        app_ids,
    ).fetchone()[0]
    items = connection.execute(
        f"SELECT count(*) FROM item WHERE id IN ({','.join('?' for _ in item_ids)})",
        item_ids,
    ).fetchone()[0]
    layouts = connection.execute(
        f"SELECT count(*) FROM item_layout "
        f"WHERE item_id IN ({','.join('?' for _ in item_ids)})",
        item_ids,
    ).fetchone()[0]
    expected_layouts = 16 * connection.execute(
        """
        SELECT count(*)
        FROM layout
        JOIN board ON board.id = layout.board_id
        WHERE board.name IN ('dashboard', 'Admin', 'default')
        """
    ).fetchone()[0]
    reader_apps = connection.execute(
        "SELECT count(*) FROM app WHERE name IN ('Audiobookshelf', 'Kavita')"
    ).fetchone()[0]
print(integrity, apps, items, layouts, expected_layouts, reader_apps)
PY
)
[[ "$homarr_integrity" == "ok" ]] ||
  fail "Homarr database integrity is $homarr_integrity"
[[ "$homarr_apps" == "16" && "$homarr_items" == "48" &&
  "$homarr_layouts" == "$expected_layouts" &&
  "$homarr_reader_apps" == "2" ]] ||
  fail "Homarr managed state is apps=$homarr_apps items=$homarr_items layouts=$homarr_layouts expected=$expected_layouts reader_apps=$homarr_reader_apps"
printf 'OK Homarr managed apps=%s items=%s layouts=%s\n' \
  "$homarr_apps" "$homarr_items" "$homarr_layouts"

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
