#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly appdata_root="/srv/appdata/docker/infra-nginx-proxy-manager"
readonly database="$appdata_root/data/database.sqlite"
readonly backup="$appdata_root/database.sqlite.pre-haos-http-route"
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
  echo "NPM database integrity is $integrity before HAOS route reconciliation" >&2
  exit 1
}

route_count="$(
  sqlite3 -readonly "$database" "
    SELECT count(*)
    FROM proxy_host
    WHERE domain_names = '[\"ha.rafael.media\"]'
      AND is_deleted = 0;
  "
)"
[[ "$route_count" == "1" ]] || {
  echo "Expected one active ha.rafael.media proxy row, found $route_count" >&2
  exit 1
}

if [[ ! -s "$backup" ]]; then
  sqlite3 -readonly "$database" ".backup '$backup'"
  chmod 0600 "$backup"
fi

sqlite3 -cmd '.timeout 30000' "$database" <<'SQL'
BEGIN IMMEDIATE;
UPDATE proxy_host
SET is_deleted = 0,
    enabled = 1,
    forward_scheme = 'http',
    forward_host = '192.168.0.125',
    forward_port = 8123,
    allow_websocket_upgrade = 1,
    modified_on = datetime('now')
WHERE domain_names = '["ha.rafael.media"]';
COMMIT;
SQL

integrity="$(sqlite3 -readonly "$database" 'PRAGMA integrity_check;')"
[[ "$integrity" == "ok" ]] || {
  echo "NPM database integrity is $integrity after HAOS route reconciliation" >&2
  exit 1
}

docker exec --interactive nginx-proxy-manager \
  node --input-type=module \
  <"$script_dir/reconcile-haos-proxy-config.mjs"
docker exec nginx-proxy-manager nginx -t >/dev/null

route_ok="$(
  sqlite3 -readonly "$database" "
    SELECT count(*)
    FROM proxy_host
    WHERE domain_names = '[\"ha.rafael.media\"]'
      AND forward_scheme = 'http'
      AND forward_host = '192.168.0.125'
      AND forward_port = 8123
      AND allow_websocket_upgrade = 1
      AND ssl_forced = 1
      AND certificate_id > 0
      AND enabled = 1
      AND is_deleted = 0;
  "
)"
[[ "$route_ok" == "1" ]] || {
  echo "ha.rafael.media did not reconcile to the declared HTTPS-to-HTTP route" >&2
  exit 1
}

echo "NPM HAOS route reconciled; focused SQLite rollback retained at $backup"
