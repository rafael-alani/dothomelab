#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly appdata_root="/srv/appdata/docker/infra-nginx-proxy-manager"
readonly database="$appdata_root/data/database.sqlite"
readonly backup="$appdata_root/database.sqlite.pre-grimmory"
readonly lock="/run/lock/dothomelab-npm-routes.lock"

[[ -s "$database" ]] || {
  echo "NPM database is missing: $database" >&2
  exit 1
}
[[ "$(docker inspect --format '{{.State.Status}}' nginx-proxy-manager)" == "running" ]] || {
  echo "NPM container is not running" >&2
  exit 1
}

exec 9>"$lock"
flock -n 9 || {
  echo "Another NPM route reconciliation is already running" >&2
  exit 1
}

integrity="$(sqlite3 -readonly "$database" 'PRAGMA integrity_check;')"
[[ "$integrity" == "ok" ]] || {
  echo "NPM database integrity is $integrity before reconciliation" >&2
  exit 1
}

if [[ ! -s "$backup" ]]; then
  sqlite3 -readonly "$database" ".backup '$backup'"
  chmod 0600 "$backup"
fi

sqlite3 -cmd '.timeout 30000' "$database" <"$script_dir/update-consolidated-routes.sql"

integrity="$(sqlite3 -readonly "$database" 'PRAGMA integrity_check;')"
[[ "$integrity" == "ok" ]] || {
  echo "NPM database integrity is $integrity after reconciliation" >&2
  exit 1
}

docker exec --interactive nginx-proxy-manager \
  node --input-type=module \
  <"$script_dir/reconcile-proxy-configs.mjs"
docker exec nginx-proxy-manager nginx -t >/dev/null

read -r paperless_count gpt_count prometheus_count loki_count \
  immichframe_count wizarr_count bar_count bar_api_count \
  bar_search_count ytdlp_count snapotter_count stirling_count \
  slskd_count aurral_count navidrome_count audiobookshelf_count kavita_count \
  n8n_count pulse_count shelfarr_count cleanuparr_count bookorbit_count grimmory_count storyteller_count \
  pinepods_count syncthing_count \
  stream_count join_stream_count < <(
  sqlite3 -readonly -separator ' ' "$database" "
    SELECT
      sum(domain_names = '[\"paperless.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8002
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"paperless-gpt.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8003
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"prometheus.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 9090
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"loki.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 3100
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"immichframe.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8080
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"wizarr.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 5690
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"bar.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8200
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"bar-api.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8201
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"bar-search.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8202
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"yt-dlp.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 3033
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"snapotter.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 1349
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'proxy_buffering off;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"pdf.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8084
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"slskd.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 5030
          AND enabled = 1
          AND is_deleted = 0
          AND instr(advanced_config, 'proxy_request_buffering off;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"aurral.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 3001
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'proxy_buffering off;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"navidrome.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 4533
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"audiobookshelf.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 13378
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'client_max_body_size 10240m;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"kavita.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 5000
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'proxy_buffering off;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"n8n.rafael.media\"]'
          AND forward_host = '192.168.0.110'
          AND forward_port = 5678
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'proxy_buffering off;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"pulse.rafael.media\"]'
          AND forward_host = '192.168.0.110'
          AND forward_port = 7655
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'proxy_buffering off;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"shelfarr.rafael.media\"]'
          AND forward_host = '192.168.0.102'
          AND forward_port = 5056
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"cleanuparr.rafael.media\"]'
          AND forward_host = '192.168.0.102'
          AND forward_port = 11011
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"bookorbit.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 3002
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"grimmory.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 6060
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'client_max_body_size 10240m;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"storyteller.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8001
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'client_max_body_size 10240m;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"pinepods.rafael.media\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8040
          AND enabled = 1
          AND is_deleted = 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'proxy_buffering off;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"syncthing.rafael.media\"]'
          AND forward_scheme = 'http'
          AND forward_host = '127.0.0.1'
          AND forward_port = 8384
          AND enabled = 1
          AND is_deleted = 0
          AND access_list_id = 0
          AND ssl_forced = 1
          AND certificate_id > 0
          AND allow_websocket_upgrade = 1
          AND instr(advanced_config, 'allow 192.168.0.0/24;') > 0
          AND instr(advanced_config, 'allow 100.64.0.0/10;') > 0
          AND instr(advanced_config, 'deny all;') > 0),
      sum(domain_names = '[\"stream.rafael.ink\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 8096
          AND enabled = 1
          AND is_deleted = 0
          AND access_list_id = 0
          AND ssl_forced = 1
          AND certificate_id > 0
          AND instr(advanced_config, 'deny all;') = 0),
      sum(domain_names = '[\"join-stream.rafael.ink\"]'
          AND forward_host = '192.168.0.112'
          AND forward_port = 5690
          AND enabled = 1
          AND is_deleted = 0
          AND access_list_id = 0
          AND ssl_forced = 1
          AND certificate_id > 0
          AND instr(advanced_config, 'deny all;') = 0)
    FROM proxy_host;
  "
)
[[ "$paperless_count" == "1" && "$gpt_count" == "1" &&
  "$prometheus_count" == "1" && "$loki_count" == "1" &&
  "$immichframe_count" == "1" && "$wizarr_count" == "1" &&
  "$bar_count" == "1" && "$bar_api_count" == "1" &&
  "$bar_search_count" == "1" && "$ytdlp_count" == "1" &&
  "$snapotter_count" == "1" && "$stirling_count" == "1" &&
  "$slskd_count" == "1" && "$aurral_count" == "1" &&
  "$navidrome_count" == "1" &&
  "$audiobookshelf_count" == "1" && "$kavita_count" == "1" &&
  "$n8n_count" == "1" && "$pulse_count" == "1" &&
  "$shelfarr_count" == "1" && "$cleanuparr_count" == "1" &&
  "$bookorbit_count" == "1" &&
  "$grimmory_count" == "1" && "$storyteller_count" == "1" && "$pinepods_count" == "1" &&
  "$syncthing_count" == "1" &&
  "$stream_count" == "1" && "$join_stream_count" == "1" ]] || {
  echo "Managed NPM route reconciliation did not produce twenty-six private and two public routes" >&2
  exit 1
}

echo "NPM managed routes reconciled: twenty-six private and two public; DroppedNeedle disabled; pre-change SQLite backup retained at $backup"
