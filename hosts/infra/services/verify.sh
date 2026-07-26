#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="${APPDATA_ROOT:-/srv/appdata/docker}"
readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-infra-services}"
readonly INFRA_HOST="${INFRA_HOST:-192.168.0.110}"
readonly REQUIRE_AGENT_HTTP="${REQUIRE_AGENT_HTTP:-true}"
readonly REQUIRE_NO_LEGACY_PROXY="${REQUIRE_NO_LEGACY_PROXY:-true}"
readonly MIN_NPM_PROXY_HOSTS="${MIN_NPM_PROXY_HOSTS:-50}"
readonly MIN_NPM_CERTIFICATES="${MIN_NPM_CERTIFICATES:-6}"
readonly EXPECTED_DDNS_DOMAINS="${EXPECTED_DDNS_DOMAINS:-rafael.ink,pictures.rafael.ink,stream.rafael.ink,join-stream.rafael.ink}"

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

container_env_value() {
  local key="$1"
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
    cloudflare-ddns |
    sed -n "s/^${key}=//p"
}

ddns_domains="$(container_env_value DOMAINS)" ||
  fail "Cloudflare DDNS DOMAINS is unavailable"
ddns_proxied="$(container_env_value PROXIED)" ||
  fail "Cloudflare DDNS PROXIED is unavailable"
ddns_ip6_provider="$(container_env_value IP6_PROVIDER)" ||
  fail "Cloudflare DDNS IP6_PROVIDER is unavailable"
[[ -n "$ddns_domains" ]] || fail "Cloudflare DDNS DOMAINS is empty"
ddns_domains_match="$(
  python3 - "$ddns_domains" "$EXPECTED_DDNS_DOMAINS" <<'PY'
import sys

actual = {domain.strip() for domain in sys.argv[1].split(",") if domain.strip()}
expected = {domain.strip() for domain in sys.argv[2].split(",") if domain.strip()}
print(int(actual == expected))
PY
)"
[[ "$ddns_domains_match" == "1" ]] ||
  fail "Cloudflare DDNS does not manage the complete declared domain set"
[[ "$ddns_proxied" == "true" ]] ||
  fail "Cloudflare DDNS fallback proxy policy is $ddns_proxied, expected true"
[[ "$ddns_ip6_provider" == "none" ]] ||
  fail "Cloudflare DDNS IPv6 provider is $ddns_ip6_provider, expected none"
printf 'OK config Cloudflare DDNS domains=4 proxied-fallback=true ipv6=disabled\n'

wud_state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    wud
)" || fail "WUD container is missing"
[[ "$wud_state" == "running healthy" ]] || fail "WUD state is $wud_state"
printf 'OK container wud                 health=healthy project=wud\n'

http_check pihole "http://$INFRA_HOST:8080/admin/"
/opt/dothomelab/hosts/infra/services/configure-pihole-dns.py --check ||
  fail "managed Pi-hole DNS records are missing"
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
read -r integrity proxy_hosts certificates ha_frame_policy < <(
  python3 - "$npm_database" <<'PY'
import sqlite3
import sys

with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    proxy_hosts = connection.execute("SELECT count(*) FROM proxy_host").fetchone()[0]
    certificates = connection.execute("SELECT count(*) FROM certificate").fetchone()[0]
    ha_frame_policy = connection.execute(
        """
        SELECT count(*)
        FROM proxy_host
        WHERE domain_names = '["ha.rafael.media"]'
          AND enabled = 1
          AND is_deleted = 0
          AND instr(
            advanced_config,
            'proxy_hide_header X-Frame-Options;'
          ) > 0
          AND instr(
            advanced_config,
            'more_set_headers "Content-Security-Policy:'
          ) > 0
          AND instr(
            advanced_config,
            'frame-ancestors ''self'' https://rafael.media'
          ) > 0
        """
    ).fetchone()[0]
print(integrity, proxy_hosts, certificates, ha_frame_policy)
PY
)
[[ "$integrity" == "ok" ]] || fail "NPM database integrity is $integrity"
[[ "$proxy_hosts" -ge "$MIN_NPM_PROXY_HOSTS" ]] ||
  fail "NPM has $proxy_hosts proxy hosts, expected at least $MIN_NPM_PROXY_HOSTS"
[[ "$certificates" -ge "$MIN_NPM_CERTIFICATES" ]] ||
  fail "NPM has $certificates certificates, expected at least $MIN_NPM_CERTIFICATES"
[[ "$ha_frame_policy" == "1" ]] ||
  fail "ha.rafael.media does not have the scoped Homarr frame policy"
printf 'OK data NPM integrity=%s proxy_hosts=%s certificates=%s\n' \
  "$integrity" "$proxy_hosts" "$certificates"
printf 'OK route ha.rafael.media permits framing only from self and https://rafael.media\n'

ha_headers="$(
  curl --silent --show-error --dump-header - --output /dev/null \
    --max-time 15 https://ha.rafael.media/
)" || fail "Home Assistant HTTPS response headers are unavailable"
if grep -Eiq '^x-frame-options:' <<<"$ha_headers"; then
  fail "ha.rafael.media still returns X-Frame-Options"
fi
grep -Eiq \
  "^content-security-policy:.*frame-ancestors 'self' https://rafael\\.media([;[:space:]]|$)" \
  <<<"$ha_headers" ||
  fail "ha.rafael.media does not return the scoped frame-ancestors policy"
printf 'OK headers Home Assistant framing is scoped to https://rafael.media\n'

read -r paperless_route paperless_gpt_route prometheus_route loki_route \
  immichframe_route wizarr_route bar_route bar_api_route \
  bar_search_route ytdlp_route snapotter_route stirling_route \
  slskd_route aurral_route navidrome_route audiobookshelf_route kavita_route \
  n8n_route pulse_route shelfarr_route cleanuparr_route bookorbit_route grimmory_route storyteller_route \
  pinepods_route syncthing_route droppedneedle_retired \
  stream_route join_stream_route < <(
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
    '["aurral.rafael.media"]': ("192.168.0.112", 3001),
    '["navidrome.rafael.media"]': ("192.168.0.112", 4533),
    '["audiobookshelf.rafael.media"]': ("192.168.0.112", 13378),
    '["kavita.rafael.media"]': ("192.168.0.112", 5000),
    '["n8n.rafael.media"]': ("192.168.0.110", 5678),
    '["pulse.rafael.media"]': ("192.168.0.110", 7655),
    '["shelfarr.rafael.media"]': ("192.168.0.102", 5056),
    '["cleanuparr.rafael.media"]': ("192.168.0.102", 11011),
    '["bookorbit.rafael.media"]': ("192.168.0.112", 3002),
    '["grimmory.rafael.media"]': ("192.168.0.112", 6060),
    '["storyteller.rafael.media"]': ("192.168.0.112", 8001),
    '["pinepods.rafael.media"]': ("192.168.0.112", 8040),
    '["syncthing.rafael.media"]': ("127.0.0.1", 8384),
}
found = {}
public_found = {}
with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
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
          '["aurral.rafael.media"]',
          '["navidrome.rafael.media"]',
          '["audiobookshelf.rafael.media"]',
          '["kavita.rafael.media"]',
          '["n8n.rafael.media"]',
          '["pulse.rafael.media"]',
          '["shelfarr.rafael.media"]',
          '["cleanuparr.rafael.media"]',
          '["bookorbit.rafael.media"]',
          '["grimmory.rafael.media"]',
          '["storyteller.rafael.media"]',
          '["pinepods.rafael.media"]',
          '["syncthing.rafael.media"]'
        )
        """
    ):
        found[domain] = (
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
            == (host, port, 1, 0, 0, 1, True, 1, True, True, True)
        )
    )
retired = connection.execute(
    """
    SELECT count(*)
    FROM proxy_host
    WHERE domain_names = '["droppedneedle.rafael.media"]'
      AND enabled = 0
      AND is_deleted = 0
    """
).fetchone()[0]
results.append(int(retired == 1))
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
  "$slskd_route" == "1" && "$aurral_route" == "1" &&
  "$navidrome_route" == "1" &&
  "$audiobookshelf_route" == "1" && "$kavita_route" == "1" &&
  "$n8n_route" == "1" && "$pulse_route" == "1" &&
  "$shelfarr_route" == "1" && "$cleanuparr_route" == "1" &&
  "$bookorbit_route" == "1" &&
  "$grimmory_route" == "1" && "$storyteller_route" == "1" && "$pinepods_route" == "1" &&
  "$syncthing_route" == "1" && "$droppedneedle_retired" == "1" &&
  "$stream_route" == "1" && "$join_stream_route" == "1" ]] ||
  fail "managed NPM routes are absent, have the wrong exposure, or target the wrong backend"
printf 'OK routes all twenty-six managed endpoints use TLS and are private to LAN/Tailscale; DroppedNeedle is disabled\n'
printf 'OK routes stream and join-stream are public with TLS and authenticated applications\n'

homarr_database="$APPDATA_ROOT/homarr/db/db.sqlite"
[[ -s "$homarr_database" ]] || fail "Homarr database is missing"
read -r homarr_integrity homarr_apps homarr_items homarr_layouts \
  expected_layouts homarr_reader_apps homarr_syncthing_app \
  homarr_syncthing_items homarr_cleanuparr_app < <(
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
    "dhlaurralapp000000000001",
    "dhlaudiobookshelfapp0001",
    "dhlkavitaapp000000000001",
    "dhln8napp000000000000001",
    "dhlpulseapp000000000001",
    "dhlsyncthingapp000000001",
    "dhlshelfarrapp00000000001",
    "dhlcleanuparrapp000000001",
    "dhlbookorbitapp000000001",
    "dhlgrimmoryapp000000001",
    "dhlstorytellerapp000001",
    "dhlpinepodsapp0000000000",
    "dhlnavidromeapp000000001",
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
    "dhlaurralitemdashboard01",
    "dhlaurralitemadmin000001",
    "dhlaurralitemdefault0001",
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
    "dhlsyncthingitemdash0001",
    "dhlsyncthingitemadmin001",
    "dhlsyncthingitemdef00001",
    "dhlshelfarritemdash00001",
    "dhlshelfarritemadmin0001",
    "dhlshelfarritemdef000001",
    "dhlcleanuparritemdash001",
    "dhlcleanuparritemadmin01",
    "dhlcleanuparritemdef0001",
    "dhlbookorbititemdash0001",
    "dhlbookorbititemadmin001",
    "dhlbookorbititemdef00001",
    "dhlgrimmoryitemdash0001",
    "dhlgrimmoryitemadmin001",
    "dhlgrimmoryitemdef00001",
    "dhlstorytelleritemdash01",
    "dhlstorytelleritemadm001",
    "dhlstorytelleritemdef001",
    "dhlpinepodsitemdash00001",
    "dhlpinepodsitemadmin0001",
    "dhlpinepodsitemdefault01",
    "dhlnavidromeitemdash001",
    "dhlnavidromeitemadmin01",
    "dhlnavidromeitemdefault1",
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
    expected_layouts = 24 * connection.execute(
        """
        SELECT count(*)
        FROM layout
        JOIN board ON board.id = layout.board_id
        WHERE board.name IN ('dashboard', 'Admin', 'default')
        """
    ).fetchone()[0]
    reader_apps = connection.execute(
        "SELECT count(*) FROM app "
        "WHERE name IN ('Audiobookshelf', 'Kavita', 'Storyteller')"
    ).fetchone()[0]
    syncthing_app = connection.execute(
        """
        SELECT count(*)
        FROM app
        WHERE id = 'dhlsyncthingapp000000001'
          AND name = 'Syncthing'
          AND href = 'https://syncthing.rafael.media'
          AND ping_url =
            'https://syncthing.rafael.media/rest/noauth/health'
        """
    ).fetchone()[0]
    syncthing_items = connection.execute(
        """
        SELECT count(*)
        FROM item
        JOIN board ON board.id = item.board_id
        WHERE item.id IN (
          'dhlsyncthingitemdash0001',
          'dhlsyncthingitemadmin001',
          'dhlsyncthingitemdef00001'
        )
          AND board.name IN ('dashboard', 'Admin', 'default')
          AND item.options LIKE
            '%"appId":"dhlsyncthingapp000000001"%'
          AND item.options LIKE '%"pingEnabled":false%'
        """
    ).fetchone()[0]
    cleanuparr_app = connection.execute(
        """
        SELECT count(*)
        FROM app
        WHERE id = 'dhlcleanuparrapp000000001'
          AND name = 'Cleanuparr'
          AND href = 'https://cleanuparr.rafael.media'
          AND ping_url = 'http://192.168.0.102:11011/health'
        """
    ).fetchone()[0]
print(
    integrity,
    apps,
    items,
    layouts,
    expected_layouts,
    reader_apps,
    syncthing_app,
    syncthing_items,
    cleanuparr_app,
)
PY
)
[[ "$homarr_integrity" == "ok" ]] ||
  fail "Homarr database integrity is $homarr_integrity"
[[ "$homarr_apps" == "24" && "$homarr_items" == "72" &&
  "$homarr_layouts" == "$expected_layouts" &&
  "$homarr_reader_apps" == "3" &&
  "$homarr_syncthing_app" == "1" &&
  "$homarr_syncthing_items" == "3" &&
  "$homarr_cleanuparr_app" == "1" ]] ||
  fail "Homarr managed state is apps=$homarr_apps items=$homarr_items layouts=$homarr_layouts expected=$expected_layouts reader_apps=$homarr_reader_apps"
printf 'OK Homarr managed apps=%s items=%s layouts=%s\n' \
  "$homarr_apps" "$homarr_items" "$homarr_layouts"
printf 'OK Homarr Syncthing link is private and its three tile pings are disabled\n'
printf 'OK Homarr Cleanuparr link and direct health ping are managed\n'

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
