#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly appdata_root="/srv/appdata/docker/infra-nginx-proxy-manager"
readonly database="$appdata_root/data/database.sqlite"
readonly backup="$appdata_root/database.sqlite.pre-paperless"
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

read -r paperless_count gpt_count < <(
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
          AND instr(advanced_config, 'deny all;') > 0)
    FROM proxy_host;
  "
)
[[ "$paperless_count" == "1" && "$gpt_count" == "1" ]] || {
  echo "Paperless NPM route reconciliation did not produce two private routes" >&2
  exit 1
}

echo "NPM Paperless routes reconciled; pre-change SQLite backup retained at $backup"
