#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_root="/srv/appdata/docker/snapotter/backups"
readonly latest="$backup_root/latest"
readonly previous="$backup_root/previous"
temporary="$(mktemp -d "$backup_root/.database-backup.XXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    snapotter-db
)"
[[ "$state" == "running healthy" ]] || {
  echo "SnapOtter PostgreSQL is not healthy: $state" >&2
  exit 1
}

install -d -m 0700 "$latest" "$previous"

docker exec snapotter-db pg_dump \
  --format=custom \
  --dbname=snapotter \
  --username=snapotter \
  >"$temporary/snapotter.dump"
docker exec snapotter-db pg_dumpall \
  --roles-only \
  --username=snapotter |
  gzip -1 >"$temporary/roles.sql.gz"
docker exec snapotter-db psql \
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
  " >"$temporary/counts.txt"
docker exec snapotter-db psql \
  --dbname=snapotter \
  --username=snapotter \
  --no-align \
  --tuples-only \
  --command="SHOW data_checksums" \
  >"$temporary/data-checksums.txt"

(
  cd "$temporary"
  sha256sum snapotter.dump roles.sql.gz counts.txt data-checksums.txt \
    >SHA256SUMS
)
chmod 0600 "$temporary"/*

for file in snapotter.dump roles.sql.gz counts.txt data-checksums.txt SHA256SUMS; do
  if [[ -s "$latest/$file" ]]; then
    install -m 0600 "$latest/$file" "$previous/$file"
  fi
  install -m 0600 "$temporary/$file" "$latest/$file"
done

echo "$latest"
