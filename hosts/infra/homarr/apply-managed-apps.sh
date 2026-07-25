#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly homarr_root="/srv/appdata/docker/homarr"
readonly database="$homarr_root/db/db.sqlite"
readonly backup="$homarr_root/db.sqlite.pre-observability"
readonly lock="/run/lock/dothomelab-homarr-apps.lock"

[[ -s "$database" ]] || {
  echo "Homarr database is missing: $database" >&2
  exit 1
}
[[ "$(docker inspect --format '{{.State.Status}}' homarr)" == "running" ]] || {
  echo "Homarr container is not running" >&2
  exit 1
}

exec 9>"$lock"
flock -n 9 || {
  echo "Another Homarr reconciliation is already running" >&2
  exit 1
}

integrity="$(sqlite3 -readonly "$database" 'PRAGMA integrity_check;')"
[[ "$integrity" == "ok" ]] || {
  echo "Homarr database integrity is $integrity before reconciliation" >&2
  exit 1
}

if [[ ! -s "$backup" ]]; then
  sqlite3 -readonly "$database" ".backup '$backup'"
  chmod 0600 "$backup"
fi

restart_pending=1
restart_homarr() {
  if ((restart_pending)); then
    docker start homarr >/dev/null 2>&1 || true
  fi
}
trap restart_homarr EXIT INT TERM

docker stop --time 30 homarr >/dev/null
sqlite3 -cmd '.timeout 30000' "$database" <"$script_dir/reconcile-managed-apps.sql"

integrity="$(sqlite3 -readonly "$database" 'PRAGMA integrity_check;')"
[[ "$integrity" == "ok" ]] || {
  echo "Homarr database integrity is $integrity after reconciliation" >&2
  exit 1
}

docker start homarr >/dev/null
restart_pending=0
trap - EXIT INT TERM

deadline=$((SECONDS + 180))
while ((SECONDS < deadline)); do
  health="$(
    docker inspect --format \
      '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
      homarr 2>/dev/null || true
  )"
  [[ "$health" == "healthy" ]] && break
  [[ "$health" == "unhealthy" ]] && {
    docker logs --tail 50 homarr >&2
    echo "Homarr became unhealthy after managed app reconciliation" >&2
    exit 1
  }
  sleep 5
done
[[ "$health" == "healthy" ]] || {
  echo "Homarr did not become healthy after managed app reconciliation" >&2
  exit 1
}

read -r apps items layouts expected_layouts < <(
  sqlite3 -readonly -separator ' ' "$database" "
    SELECT
      (SELECT count(*) FROM app
       WHERE id IN (
         'dhlpaperlessngxapp000001',
         'dhlpaperlessgptapp000001',
         'dhlprometheusapp000001',
         'dhllokiapp000000000001'
       )),
      (SELECT count(*) FROM item
       WHERE id IN (
         'dhlpaperlessngxitemdash1',
         'dhlpaperlessgptitemdash1',
         'dhlpaperlessngxitemadm01',
         'dhlpaperlessgptitemadm01',
         'dhlpaperlessngxitemdef01',
         'dhlpaperlessgptitemdef01',
         'dhlprometheusitemdash1',
         'dhllokiitemdashboard001',
         'dhlprometheusitemadm01',
         'dhllokiitemadmin000001',
         'dhlprometheusitemdef01',
         'dhllokiitemdefault0001'
       )),
      (SELECT count(*) FROM item_layout
       WHERE item_id IN (
         'dhlpaperlessngxitemdash1',
         'dhlpaperlessgptitemdash1',
         'dhlpaperlessngxitemadm01',
         'dhlpaperlessgptitemadm01',
         'dhlpaperlessngxitemdef01',
         'dhlpaperlessgptitemdef01',
         'dhlprometheusitemdash1',
         'dhllokiitemdashboard001',
         'dhlprometheusitemadm01',
         'dhllokiitemadmin000001',
         'dhlprometheusitemdef01',
         'dhllokiitemdefault0001'
       )),
      4 * (
        SELECT count(*)
        FROM layout
        JOIN board ON board.id = layout.board_id
        WHERE board.name IN ('dashboard', 'Admin', 'default')
      );
  "
)
[[ "$apps" == "4" && "$items" == "12" && "$layouts" == "$expected_layouts" ]] || {
  echo "Homarr managed state is apps=$apps items=$items layouts=$layouts expected_layouts=$expected_layouts" >&2
  exit 1
}

echo "Homarr managed tiles reconciled; pre-change SQLite backup retained at $backup"
