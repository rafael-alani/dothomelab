#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="${APPDATA_ROOT:-/srv/appdata/docker}"
readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-infra-services}"
readonly INFRA_HOST="${INFRA_HOST:-192.168.0.110}"
readonly REQUIRE_AGENT_HTTP="${REQUIRE_AGENT_HTTP:-true}"
readonly REQUIRE_NO_LEGACY_PROXY="${REQUIRE_NO_LEGACY_PROXY:-true}"
readonly MIN_NPM_PROXY_HOSTS="${MIN_NPM_PROXY_HOSTS:-40}"
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

read -r paperless_route paperless_gpt_route prometheus_route loki_route < <(
  python3 - "$npm_database" <<'PY'
import sqlite3
import sys

expected = {
    '["paperless.rafael.media"]': ("192.168.0.112", 8002),
    '["paperless-gpt.rafael.media"]': ("192.168.0.112", 8003),
    '["prometheus.rafael.media"]': ("192.168.0.112", 9090),
    '["loki.rafael.media"]': ("192.168.0.112", 3100),
}
found = {}
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
          '["loki.rafael.media"]'
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

results = []
for domain, (host, port) in expected.items():
    results.append(
        int(
            found.get(domain)
            == (host, port, 1, 0, True, True, True)
        )
    )
print(*results)
PY
)
[[ "$paperless_route" == "1" && "$paperless_gpt_route" == "1" &&
  "$prometheus_route" == "1" && "$loki_route" == "1" ]] ||
  fail "managed NPM routes are absent, public, or target the wrong backend"
printf 'OK routes all four managed Apps services are private to LAN/Tailscale\n'

homarr_database="$APPDATA_ROOT/homarr/db/db.sqlite"
[[ -s "$homarr_database" ]] || fail "Homarr database is missing"
read -r homarr_integrity homarr_apps homarr_items homarr_layouts expected_layouts < <(
  python3 - "$homarr_database" <<'PY'
import sqlite3
import sys

app_ids = (
    "dhlpaperlessngxapp000001",
    "dhlpaperlessgptapp000001",
    "dhlprometheusapp000001",
    "dhllokiapp000000000001",
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
    expected_layouts = 4 * connection.execute(
        """
        SELECT count(*)
        FROM layout
        JOIN board ON board.id = layout.board_id
        WHERE board.name IN ('dashboard', 'Admin', 'default')
        """
    ).fetchone()[0]
print(integrity, apps, items, layouts, expected_layouts)
PY
)
[[ "$homarr_integrity" == "ok" ]] ||
  fail "Homarr database integrity is $homarr_integrity"
[[ "$homarr_apps" == "4" && "$homarr_items" == "12" &&
  "$homarr_layouts" == "$expected_layouts" ]] ||
  fail "Homarr managed state is apps=$homarr_apps items=$homarr_items layouts=$homarr_layouts expected=$expected_layouts"
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
