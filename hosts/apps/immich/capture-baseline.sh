#!/usr/bin/env bash
set -euo pipefail

target="${1:?Usage: $0 <existing-backup-directory>}"
[[ -d "$target" ]] || {
  echo "Backup directory does not exist: $target" >&2
  exit 2
}

database_container="immich_migration_postgres"
server_container="immich_migration_server"

docker exec "$database_container" sh -ec '
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
    --no-align --tuples-only --field-separator="=" --command="
      SELECT metric, value
      FROM (
        SELECT 10 AS sequence, '\''users'\'' AS metric, count(*)::text AS value FROM users
        UNION ALL SELECT 20, '\''assets'\'', count(*)::text FROM assets
        UNION ALL SELECT 21, '\''assets_managed'\'', count(*)::text FROM assets WHERE NOT \"isExternal\"
        UNION ALL SELECT 22, '\''assets_external'\'', count(*)::text FROM assets WHERE \"isExternal\"
        UNION ALL SELECT 23, '\''assets_offline'\'', count(*)::text FROM assets WHERE \"isOffline\"
        UNION ALL SELECT 24, '\''assets_deleted'\'', count(*)::text FROM assets WHERE \"deletedAt\" IS NOT NULL
        UNION ALL SELECT 30, '\''albums'\'', count(*)::text FROM albums
        UNION ALL SELECT 31, '\''album_assets'\'', count(*)::text FROM albums_assets_assets
        UNION ALL SELECT 40, '\''libraries'\'', count(*)::text FROM libraries
        UNION ALL SELECT 50, '\''people'\'', count(*)::text FROM person
        UNION ALL SELECT 51, '\''faces'\'', count(*)::text FROM asset_faces
        UNION ALL SELECT 60, '\''memories'\'', count(*)::text FROM memories
        UNION ALL SELECT 70, '\''shared_links'\'', count(*)::text FROM shared_links
        UNION ALL SELECT 80, '\''tags'\'', count(*)::text FROM tags
      ) AS baseline
      ORDER BY sequence
    "
' >"$target/baseline-counts.txt"

docker exec "$database_container" sh -ec '
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
    --no-align --tuples-only --command="
      COPY (
        SELECT id::text, \"isExternal\"::text, \"originalPath\"
        FROM assets
        WHERE \"deletedAt\" IS NULL
        ORDER BY \"isExternal\", id
      ) TO STDOUT WITH (FORMAT csv, DELIMITER E'\''\t'\'')
    "
' >"$target/asset-paths.tsv"

docker exec "$database_container" sh -ec '
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
    --no-align --tuples-only --command="
      (SELECT \"originalPath\" FROM assets
       WHERE \"deletedAt\" IS NULL AND NOT \"isExternal\" ORDER BY id LIMIT 10)
      UNION ALL
      (SELECT \"originalPath\" FROM assets
       WHERE \"deletedAt\" IS NULL AND \"isExternal\" ORDER BY id LIMIT 10)
    "
' >"$target/representative-paths.txt"

checked=0
while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  docker exec "$server_container" test -r "$path"
  checked=$((checked + 1))
done <"$target/representative-paths.txt"
[[ "$checked" -eq 20 ]] || {
  echo "Expected 20 representative paths, verified $checked" >&2
  exit 1
}

sha256sum "$target/asset-paths.tsv" >"$target/asset-paths.sha256"
chmod 0600 \
  "$target/baseline-counts.txt" \
  "$target/asset-paths.tsv" \
  "$target/asset-paths.sha256" \
  "$target/representative-paths.txt"

cat "$target/baseline-counts.txt"
echo "representative_paths_readable=$checked"
