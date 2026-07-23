#!/usr/bin/env bash
set -euo pipefail

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

curl --fail --silent --show-error http://127.0.0.1:2283/api/server-info/ping >/dev/null

docker exec immich_migration_postgres sh -ec '
  pg_isready --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" --no-align --tuples-only \
    --command="SELECT COALESCE(SUM(checksum_failures), 0) FROM pg_stat_database" |
    grep -qx 0
  psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" --no-align --tuples-only \
    --command="SELECT extname || E'\''='\'' || extversion FROM pg_extension ORDER BY extname"
'

docker exec immich_migration_server test -r /usr/src/app/upload/.immich
docker exec immich_migration_server find /usr/src/app/upload -type f -print -quit | grep -q .
docker exec immich_migration_server find /old-photos -type f -print -quit | grep -q .

echo "Immich recovery verification passed"
