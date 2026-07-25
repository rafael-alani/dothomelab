#!/usr/bin/env bash
set -Eeuo pipefail

# The Paperless-ngx project owns the application-local PostgreSQL service.
readonly backup_root="/srv/appdata/docker/paperless/backups"
readonly latest="$backup_root/latest"
readonly previous="$backup_root/previous"
temporary="$(mktemp -d "$backup_root/.database-backup.XXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    paperless-db
)"
[[ "$state" == "running healthy" ]] || {
  echo "Paperless PostgreSQL is not healthy: $state" >&2
  exit 1
}

install -d -m 0700 "$latest" "$previous"

docker exec paperless-db sh -ec \
  'pg_dump --format=custom --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"' \
  >"$temporary/paperless.dump"
docker exec paperless-db sh -ec \
  'pg_dumpall --roles-only --username="$POSTGRES_USER"' |
  gzip -1 >"$temporary/roles.sql.gz"
docker exec paperless-db sh -ec '
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
    --no-align --tuples-only --field-separator="=" --command="
      SELECT metric, value
      FROM (
        SELECT 10 AS sequence, '\''users'\'' AS metric, count(*)::text AS value
          FROM auth_user
        UNION ALL
        SELECT 20, '\''documents'\'', count(*)::text
          FROM documents_document
      ) AS counts
      ORDER BY sequence
    "
' >"$temporary/counts.txt"
docker exec paperless-db sh -ec '
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
    --no-align --tuples-only --command="SHOW data_checksums"
' >"$temporary/data-checksums.txt"

(
  cd "$temporary"
  sha256sum paperless.dump roles.sql.gz counts.txt data-checksums.txt \
    >SHA256SUMS
)
chmod 0600 "$temporary"/*

for file in paperless.dump roles.sql.gz counts.txt data-checksums.txt SHA256SUMS; do
  if [[ -s "$latest/$file" ]]; then
    install -m 0600 "$latest/$file" "$previous/$file"
  fi
  install -m 0600 "$temporary/$file" "$latest/$file"
done

echo "$latest"
