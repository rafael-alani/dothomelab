#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_root="/srv/appdata/docker/bookorbit/backups"
readonly latest="$backup_root/latest"
readonly previous="$backup_root/previous"
temporary="$(mktemp -d "$backup_root/.database-backup.XXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    bookorbit-db
)"
[[ "$state" == "running healthy" ]] || {
  echo "BookOrbit PostgreSQL is not healthy: $state" >&2
  exit 1
}

install -d -m 0700 "$latest" "$previous"
docker exec bookorbit-db pg_dump \
  --format=custom \
  --dbname=bookorbit \
  --username=bookorbit \
  >"$temporary/bookorbit.dump"
docker exec bookorbit-db pg_dumpall \
  --roles-only \
  --username=bookorbit |
  gzip -1 >"$temporary/roles.sql.gz"
docker exec bookorbit-db psql \
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
  " >"$temporary/counts.txt"
docker exec bookorbit-db psql \
  --dbname=bookorbit \
  --username=bookorbit \
  --no-align \
  --tuples-only \
  --command="
    SELECT extname || '=' || extversion
    FROM pg_extension
    WHERE extname IN ('uuid-ossp', 'pg_trgm', 'unaccent', 'vector')
    ORDER BY extname
  " >"$temporary/extensions.txt"

(
  cd "$temporary"
  sha256sum bookorbit.dump roles.sql.gz counts.txt extensions.txt >SHA256SUMS
)
chmod 0600 "$temporary"/*

for file in bookorbit.dump roles.sql.gz counts.txt extensions.txt SHA256SUMS; do
  if [[ -s "$latest/$file" ]]; then
    install -m 0600 "$latest/$file" "$previous/$file"
  fi
  install -m 0600 "$temporary/$file" "$latest/$file"
done

echo "$latest"
