#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_dir="${1:-/srv/appdata/docker/paperless/backups/latest}"
[[ -s "$backup_dir/paperless.dump" && -s "$backup_dir/SHA256SUMS" ]] || {
  echo "Paperless backup is incomplete: $backup_dir" >&2
  exit 2
}

(
  cd "$backup_dir"
  sha256sum --check SHA256SUMS
)

get_env() {
  local key="$1"
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' paperless-db |
    sed -n "s/^${key}=//p"
}

db_name="$(get_env POSTGRES_DB)"
db_user="$(get_env POSTGRES_USER)"
db_password="$(get_env POSTGRES_PASSWORD)"
[[ -n "$db_name" && -n "$db_user" && -n "$db_password" ]]

timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
container="paperless_restore_test_${timestamp,,}"
container="${container//[^a-z0-9_.-]/_}"
data_path="/srv/appdata/docker/paperless/restore-tests/$timestamp"
install -d -o 999 -g 999 -m 0700 "$data_path"

docker run --detach \
  --name "$container" \
  --network none \
  --label dothomelab.restore-test=paperless \
  --env "POSTGRES_DB=$db_name" \
  --env "POSTGRES_USER=$db_user" \
  --env "POSTGRES_PASSWORD=$db_password" \
  --env POSTGRES_INITDB_ARGS=--data-checksums \
  --volume "$data_path:/var/lib/postgresql" \
  postgres:18 >/dev/null

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
    --dbname="$db_name" --username="$db_user" >/dev/null 2>&1; then
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
    --dbname="$db_name" \
    --username="$db_user" \
    --clean \
    --if-exists \
    --no-owner \
    --exit-on-error <"$backup_dir/paperless.dump" >/dev/null

docker exec "$container" psql \
  --dbname="$db_name" \
  --username="$db_user" \
  --no-align \
  --tuples-only \
  --field-separator="=" \
  --command="
    SELECT metric, value
    FROM (
      SELECT 10 AS sequence, 'users' AS metric, count(*)::text AS value
        FROM auth_user
      UNION ALL
      SELECT 20, 'documents', count(*)::text
        FROM documents_document
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

printf 'Paperless restore test passed.\ncontainer=%s\ndata_path=%s\n' \
  "$container" "$data_path"
