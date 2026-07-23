#!/usr/bin/env bash
set -euo pipefail

checkpoint="${1:?Usage: $0 <checkpoint-name>}"
[[ "$checkpoint" =~ ^[a-zA-Z0-9._-]+$ ]] || {
  echo "Invalid checkpoint name: $checkpoint" >&2
  exit 2
}

backup_root="/srv/appdata/docker/immich/backups"
timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
target="$backup_root/${timestamp}-${checkpoint}"

install -d -m 0700 "$target"

docker exec immich_migration_postgres sh -ec \
  'pg_dump --clean --if-exists --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"' |
  gzip -1 >"$target/immich.sql.gz"

docker exec immich_migration_postgres sh -ec \
  'pg_dumpall --roles-only --username="$POSTGRES_USER"' |
  gzip -1 >"$target/roles.sql.gz"

docker exec immich_migration_postgres sh -ec \
  'psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" --no-align --tuples-only \
    --command="SELECT extname || E'\''='\'' || extversion FROM pg_extension ORDER BY extname"' \
  >"$target/extensions.txt"

sha256sum "$target"/* >"$target/SHA256SUMS"
chmod 0600 "$target"/*

echo "$target"
