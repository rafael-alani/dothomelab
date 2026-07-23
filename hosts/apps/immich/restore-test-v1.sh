#!/usr/bin/env bash
set -euo pipefail

backup_dir="${1:?Usage: $0 <backup-directory>}"
[[ -r "$backup_dir/immich.sql.gz" ]] || {
  echo "Missing database dump: $backup_dir/immich.sql.gz" >&2
  exit 2
}
[[ -r "$backup_dir/baseline-counts.txt" ]] || {
  echo "Missing baseline counts: $backup_dir/baseline-counts.txt" >&2
  exit 2
}

(
  cd "$backup_dir"
  sha256sum --check SHA256SUMS
)

source_container="immich_migration_postgres"
timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
container="immich_restore_test_${timestamp,,}"
container="${container//[^a-z0-9_.-]/_}"
data_path="/srv/appdata/docker/immich/restore-tests/$timestamp-v1.124.2"

get_env() {
  local key="$1"
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$source_container" |
    sed -n "s/^${key}=//p"
}

db_name="$(get_env POSTGRES_DB)"
db_user="$(get_env POSTGRES_USER)"
db_password="$(get_env POSTGRES_PASSWORD)"
[[ -n "$db_name" && -n "$db_user" && -n "$db_password" ]]

install -d -m 0700 "$data_path"

docker run --detach \
  --name "$container" \
  --network none \
  --label dothomelab.restore-test=immich-v1.124.2 \
  --env "POSTGRES_DB=$db_name" \
  --env "POSTGRES_USER=$db_user" \
  --env "POSTGRES_PASSWORD=$db_password" \
  --env POSTGRES_INITDB_ARGS=--data-checksums \
  --volume "$data_path:/var/lib/postgresql/data" \
  docker.io/tensorchord/pgvecto-rs:pg14-v0.2.0@sha256:90724186f0a3517cf6914295b5ab410db9ce23190a2d9d0b9dd6463e3fa298f0 \
  postgres \
  -c shared_preload_libraries=vectors.so \
  -c 'search_path="$user", public, vectors' \
  -c logging_collector=on \
  -c max_wal_size=2GB \
  -c shared_buffers=512MB \
  -c wal_compression=on >/dev/null

cleanup_pending=1
cleanup() {
  if [[ "$cleanup_pending" -eq 1 ]]; then
    docker stop "$container" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

ready=0
for _ in {1..60}; do
  if docker exec "$container" psql --dbname="$db_name" --username="$db_user" \
    --no-align --tuples-only --command="SELECT 1" 2>/dev/null | grep -qx 1; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" -eq 1 ]] || {
  docker logs "$container" >&2
  docker stop "$container" >/dev/null 2>&1 || true
  echo "Restore-test PostgreSQL did not become ready" >&2
  exit 1
}

gzip --decompress --stdout "$backup_dir/immich.sql.gz" |
  docker exec --interactive "$container" \
    psql --dbname="$db_name" --username="$db_user" \
    --single-transaction --set ON_ERROR_STOP=on >/dev/null

docker exec "$container" psql --dbname="$db_name" --username="$db_user" \
  --no-align --tuples-only --field-separator="=" --command="
    SELECT metric, value
    FROM (
      SELECT 10 AS sequence, 'users' AS metric, count(*)::text AS value FROM users
      UNION ALL SELECT 20, 'assets', count(*)::text FROM assets
      UNION ALL SELECT 21, 'assets_managed', count(*)::text FROM assets WHERE NOT \"isExternal\"
      UNION ALL SELECT 22, 'assets_external', count(*)::text FROM assets WHERE \"isExternal\"
      UNION ALL SELECT 23, 'assets_offline', count(*)::text FROM assets WHERE \"isOffline\"
      UNION ALL SELECT 24, 'assets_deleted', count(*)::text FROM assets WHERE \"deletedAt\" IS NOT NULL
      UNION ALL SELECT 30, 'albums', count(*)::text FROM albums
      UNION ALL SELECT 31, 'album_assets', count(*)::text FROM albums_assets_assets
      UNION ALL SELECT 40, 'libraries', count(*)::text FROM libraries
      UNION ALL SELECT 50, 'people', count(*)::text FROM person
      UNION ALL SELECT 51, 'faces', count(*)::text FROM asset_faces
      UNION ALL SELECT 60, 'memories', count(*)::text FROM memories
      UNION ALL SELECT 70, 'shared_links', count(*)::text FROM shared_links
      UNION ALL SELECT 80, 'tags', count(*)::text FROM tags
    ) AS baseline
    ORDER BY sequence
  " >"$backup_dir/restore-test-counts.txt"

docker exec "$container" psql --dbname="$db_name" --username="$db_user" \
  --no-align --tuples-only \
  --command="SELECT extname || E'=' || extversion FROM pg_extension ORDER BY extname" \
  >"$backup_dir/restore-test-extensions.txt"

cmp "$backup_dir/baseline-counts.txt" "$backup_dir/restore-test-counts.txt"
cmp "$backup_dir/extensions.txt" "$backup_dir/restore-test-extensions.txt"

sha256sum \
  "$backup_dir/restore-test-counts.txt" \
  "$backup_dir/restore-test-extensions.txt" \
  >"$backup_dir/RESTORE-TEST-SHA256SUMS"
chmod 0600 \
  "$backup_dir/restore-test-counts.txt" \
  "$backup_dir/restore-test-extensions.txt" \
  "$backup_dir/RESTORE-TEST-SHA256SUMS"

docker stop "$container" >/dev/null
cleanup_pending=0
trap - EXIT INT TERM
printf 'container=%s\ndata_path=%s\n' "$container" "$data_path" \
  >"$backup_dir/restore-test.txt"
chmod 0600 "$backup_dir/restore-test.txt"

echo "Immich v1.124.2 restore test passed"
