#!/usr/bin/env bash
set -euo pipefail

expected_version="${1:-}"

containers=(
  immich_migration_postgres
  immich_migration_redis
  immich_migration_machine_learning
  immich_migration_server
)

for container in "${containers[@]}"; do
  status="$(docker inspect -f '{{.State.Status}}' "$container")"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container")"
  [[ "$status" == "running" ]] || {
    echo "$container is $status" >&2
    exit 1
  }
  [[ "$health" == "healthy" ]] || {
    echo "$container health is $health" >&2
    exit 1
  }
done

curl --fail --silent --show-error http://127.0.0.1:2283/api/server/ping >/dev/null
version_json="$(
  curl --fail --silent --show-error http://127.0.0.1:2283/api/server/version
)"
version="$(
  sed -n \
    's/.*"major":\([0-9][0-9]*\).*"minor":\([0-9][0-9]*\).*"patch":\([0-9][0-9]*\).*/\1.\2.\3/p' \
    <<<"$version_json"
)"
[[ -n "$version" ]] || {
  echo "Could not parse Immich version from $version_json" >&2
  exit 1
}
if [[ -n "$expected_version" ]]; then
  [[ "$version" == "${expected_version#v}" ]] || {
    echo "Expected Immich ${expected_version#v}, found $version" >&2
    exit 1
  }
fi
echo "version=$version"

docker exec immich_migration_postgres sh -ec '
  pg_isready --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" --no-align --tuples-only \
    --command="SELECT COALESCE(SUM(checksum_failures), 0) FROM pg_stat_database" |
    grep -qx 0
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" --no-align --tuples-only \
    --command="SELECT extname || E'\''='\'' || extversion FROM pg_extension ORDER BY extname"
'

docker exec immich_migration_postgres sh -ec '
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
    --no-align --tuples-only --field-separator="=" --command="
      SELECT metric, value
      FROM (
        SELECT 10 AS sequence, '\''users'\'' AS metric, count(*)::text AS value FROM \"user\"
        UNION ALL SELECT 20, '\''assets'\'', count(*)::text FROM asset
        UNION ALL SELECT 21, '\''assets_managed'\'', count(*)::text FROM asset WHERE NOT \"isExternal\"
        UNION ALL SELECT 22, '\''assets_external'\'', count(*)::text FROM asset WHERE \"isExternal\"
        UNION ALL SELECT 23, '\''assets_offline'\'', count(*)::text FROM asset WHERE \"isOffline\"
        UNION ALL SELECT 24, '\''assets_deleted'\'', count(*)::text FROM asset WHERE \"deletedAt\" IS NOT NULL
        UNION ALL SELECT 30, '\''albums'\'', count(*)::text FROM album
        UNION ALL SELECT 31, '\''album_assets'\'', count(*)::text FROM album_asset
        UNION ALL SELECT 40, '\''libraries'\'', count(*)::text FROM library
        UNION ALL SELECT 50, '\''people'\'', count(*)::text FROM person
        UNION ALL SELECT 51, '\''faces'\'', count(*)::text FROM asset_face
        UNION ALL SELECT 60, '\''shared_links'\'', count(*)::text FROM shared_link
        UNION ALL SELECT 70, '\''tags'\'', count(*)::text FROM tag
      ) AS counts
      ORDER BY sequence
    "
'

checked=0
while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  docker exec immich_migration_server test -r "$path"
  checked=$((checked + 1))
done < <(
  docker exec immich_migration_postgres sh -ec '
    psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
      --no-align --tuples-only --command="
        (SELECT \"originalPath\" FROM asset
         WHERE \"deletedAt\" IS NULL AND NOT \"isExternal\" ORDER BY id LIMIT 5)
        UNION ALL
        (SELECT \"originalPath\" FROM asset
         WHERE \"deletedAt\" IS NULL AND \"isExternal\" ORDER BY id LIMIT 5)
      "
  '
)
[[ "$checked" -eq 10 ]] || {
  echo "Expected 10 representative paths, verified $checked" >&2
  exit 1
}

echo "representative_paths_readable=$checked"
echo "Immich focused verification passed"
