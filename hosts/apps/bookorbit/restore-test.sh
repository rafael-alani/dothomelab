#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_dir="${1:-/srv/appdata/docker/bookorbit/backups/latest}"
[[ -s "$backup_dir/bookorbit.dump" && -s "$backup_dir/SHA256SUMS" ]] || {
  echo "BookOrbit backup is incomplete: $backup_dir" >&2
  exit 2
}

(
  cd "$backup_dir"
  sha256sum --check SHA256SUMS
)

db_password="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
    bookorbit-db |
    sed -n 's/^POSTGRES_PASSWORD=//p'
)"
[[ -n "$db_password" ]]

timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
container="bookorbit_restore_test_${timestamp,,}"
container="${container//[^a-z0-9_.-]/_}"
data_path="/srv/appdata/docker/bookorbit/restore-tests/$timestamp"
install -d -o 999 -g 999 -m 0700 "$data_path"

docker run --detach \
  --name "$container" \
  --network none \
  --label dothomelab.restore-test=bookorbit \
  --env POSTGRES_DB=bookorbit \
  --env POSTGRES_USER=bookorbit \
  --env "POSTGRES_PASSWORD=$db_password" \
  --env PGDATA=/var/lib/postgresql/data/pgdata \
  --volume "$data_path:/var/lib/postgresql/data" \
  pgvector/pgvector:pg18 >/dev/null

cleanup_pending=1
cleanup() {
  if [[ "$cleanup_pending" -eq 1 ]]; then
    docker stop "$container" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

ready_streak=0
for _ in {1..120}; do
  if docker exec "$container" pg_isready \
    --dbname=bookorbit --username=bookorbit >/dev/null 2>&1; then
    ready_streak=$((ready_streak + 1))
    [[ "$ready_streak" -ge 5 ]] && break
  else
    ready_streak=0
  fi
  sleep 1
done
[[ "$ready_streak" -ge 5 ]] || {
  docker logs "$container" >&2
  exit 1
}

docker exec --interactive "$container" pg_restore \
  --dbname=bookorbit \
  --username=bookorbit \
  --clean \
  --if-exists \
  --no-owner \
  --exit-on-error <"$backup_dir/bookorbit.dump" >/dev/null

docker exec "$container" psql \
  --dbname=bookorbit \
  --username=bookorbit \
  --no-align \
  --tuples-only \
  --field-separator="=" \
  --command="
    SELECT metric, value
    FROM (
      SELECT 10 AS sequence, 'users' AS metric, count(*)::text AS value FROM users
      UNION ALL
      SELECT 20, 'libraries', count(*)::text FROM libraries
      UNION ALL
      SELECT 30, 'books', count(*)::text FROM books
    ) AS counts
    ORDER BY sequence
  " >"$data_path/restore-test-counts.txt"

docker exec "$container" psql \
  --dbname=bookorbit \
  --username=bookorbit \
  --no-align \
  --tuples-only \
  --command="
    SELECT extname || '=' || extversion
    FROM pg_extension
    WHERE extname IN ('uuid-ossp', 'pg_trgm', 'unaccent', 'vector')
    ORDER BY extname
  " >"$data_path/restore-test-extensions.txt"

cmp "$backup_dir/counts.txt" "$data_path/restore-test-counts.txt"
cmp "$backup_dir/extensions.txt" "$data_path/restore-test-extensions.txt"
sha256sum \
  "$data_path/restore-test-counts.txt" \
  "$data_path/restore-test-extensions.txt" \
  >"$data_path/RESTORE-TEST-SHA256SUMS"
chmod 0600 \
  "$data_path/restore-test-counts.txt" \
  "$data_path/restore-test-extensions.txt" \
  "$data_path/RESTORE-TEST-SHA256SUMS"

docker stop "$container" >/dev/null
cleanup_pending=0
trap - EXIT INT TERM

printf 'BookOrbit restore test passed.\ncontainer=%s\ndata_path=%s\n' \
  "$container" "$data_path"
