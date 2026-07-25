#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_dir="${1:-/srv/appdata/docker/snapotter/backups/latest}"
[[ -s "$backup_dir/snapotter.dump" && -s "$backup_dir/SHA256SUMS" ]] || {
  echo "SnapOtter backup is incomplete: $backup_dir" >&2
  exit 2
}

(
  cd "$backup_dir"
  sha256sum --check SHA256SUMS
)

db_password="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
    snapotter-db |
    sed -n 's/^POSTGRES_PASSWORD=//p'
)"
[[ -n "$db_password" ]]

timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
container="snapotter_restore_test_${timestamp,,}"
container="${container//[^a-z0-9_.-]/_}"
data_path="/srv/appdata/docker/snapotter/restore-tests/$timestamp"
install -d -o 70 -g 70 -m 0700 "$data_path"

docker run --detach \
  --name "$container" \
  --network none \
  --label dothomelab.restore-test=snapotter \
  --env POSTGRES_DB=snapotter \
  --env POSTGRES_USER=snapotter \
  --env "POSTGRES_PASSWORD=$db_password" \
  --env POSTGRES_INITDB_ARGS=--data-checksums \
  --volume "$data_path:/var/lib/postgresql/data" \
  postgres:17-alpine >/dev/null

cleanup_pending=1
cleanup() {
  if [[ "$cleanup_pending" -eq 1 ]]; then
    docker stop "$container" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

ready=0
for _ in {1..60}; do
  if docker exec "$container" pg_isready \
    --dbname=snapotter --username=snapotter >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" -eq 1 ]] || {
  docker logs "$container" >&2
  exit 1
}

docker exec --interactive "$container" \
  pg_restore \
    --dbname=snapotter \
    --username=snapotter \
    --clean \
    --if-exists \
    --no-owner \
    --exit-on-error <"$backup_dir/snapotter.dump" >/dev/null

docker exec "$container" psql \
  --dbname=snapotter \
  --username=snapotter \
  --no-align \
  --tuples-only \
  --field-separator="=" \
  --command="
    SELECT metric, value
    FROM (
      SELECT 10 AS sequence, 'users' AS metric, count(*)::text AS value
        FROM users
      UNION ALL
      SELECT 20, 'user_files', count(*)::text
        FROM user_files
      UNION ALL
      SELECT 30, 'pipelines', count(*)::text
        FROM pipelines
    ) AS counts
    ORDER BY sequence
  " >"$data_path/restore-test-counts.txt"

cmp "$backup_dir/counts.txt" "$data_path/restore-test-counts.txt"
sha256sum "$data_path/restore-test-counts.txt" \
  >"$data_path/RESTORE-TEST-SHA256SUMS"
chmod 0600 \
  "$data_path/restore-test-counts.txt" \
  "$data_path/RESTORE-TEST-SHA256SUMS"

docker stop "$container" >/dev/null
cleanup_pending=0
trap - EXIT INT TERM

printf 'SnapOtter restore test passed.\ncontainer=%s\ndata_path=%s\n' \
  "$container" "$data_path"
