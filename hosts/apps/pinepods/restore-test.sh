#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_dir="${1:-/srv/appdata/docker/pinepods/backups/latest}"
[[ -s "$backup_dir/pinepods.dump" && -s "$backup_dir/SHA256SUMS" ]] || {
  echo "PinePods backup is incomplete: $backup_dir" >&2
  exit 2
}
(
  cd "$backup_dir"
  sha256sum --check SHA256SUMS
)

db_password="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' pinepods-db |
    sed -n 's/^POSTGRES_PASSWORD=//p'
)"
[[ -n "$db_password" ]]

timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
suffix="${timestamp,,}"
db_container="pinepods_restore_db_$suffix"
valkey_container="pinepods_restore_valkey_$suffix"
app_container="pinepods_restore_app_$suffix"
network="pinepods_restore_$suffix"
data_path="/srv/appdata/docker/pinepods/restore-tests/$timestamp"
install -d -o 1000 -g 1000 -m 0700 \
  "$data_path" \
  "$data_path/app-backups" \
  "$data_path/downloads"
install -d -o 999 -g 999 -m 0700 "$data_path/postgres"

docker network create --internal \
  --label dothomelab.restore-test=pinepods \
  "$network" >/dev/null
docker run --detach \
  --name "$db_container" \
  --network "$network" \
  --label dothomelab.restore-test=pinepods \
  --env POSTGRES_DB=pinepods \
  --env POSTGRES_USER=pinepods \
  --env "POSTGRES_PASSWORD=$db_password" \
  --env PGDATA=/var/lib/pgdata/pgdata \
  --volume "$data_path/postgres:/var/lib/pgdata" \
  postgres:18 >/dev/null
docker run --detach \
  --name "$valkey_container" \
  --network "$network" \
  --label dothomelab.restore-test=pinepods \
  valkey/valkey:8-alpine \
  valkey-server --save "" --appendonly no --requirepass restore-test-only >/dev/null

cleanup_pending=1
cleanup() {
  if [[ "$cleanup_pending" -eq 1 ]]; then
    docker stop "$app_container" "$valkey_container" "$db_container" \
      >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

ready_streak=0
for _ in {1..120}; do
  if docker exec "$db_container" pg_isready \
    --dbname=pinepods --username=pinepods >/dev/null 2>&1; then
    ready_streak=$((ready_streak + 1))
    [[ "$ready_streak" -ge 5 ]] && break
  else
    ready_streak=0
  fi
  sleep 1
done
[[ "$ready_streak" -ge 5 ]] || {
  docker logs "$db_container" >&2
  exit 1
}

docker exec --interactive "$db_container" pg_restore \
  --dbname=pinepods \
  --username=pinepods \
  --clean \
  --if-exists \
  --no-owner \
  --exit-on-error <"$backup_dir/pinepods.dump" >/dev/null

query_counts() {
  docker exec "$1" psql \
    --dbname=pinepods \
    --username=pinepods \
    --no-align \
    --tuples-only \
    --field-separator="=" \
    --command="
      SELECT metric, value
      FROM (
        SELECT 10 AS sequence, 'users' AS metric, count(*)::text AS value FROM \"Users\"
        UNION ALL
        SELECT 20, 'podcasts', count(*)::text FROM \"Podcasts\"
        UNION ALL
        SELECT 30, 'episodes', count(*)::text FROM \"Episodes\"
        UNION ALL
        SELECT 40, 'downloads', count(*)::text FROM \"DownloadedEpisodes\"
        UNION ALL
        SELECT 50, 'progress', count(*)::text FROM \"UserEpisodeHistory\"
        UNION ALL
        SELECT 60, 'gpodder_devices', count(*)::text FROM \"GpodderDevices\"
        UNION ALL
        SELECT 70, 'api_keys', count(*)::text FROM \"APIKeys\"
      ) AS counts
      ORDER BY sequence
    "
}

query_counts "$db_container" >"$data_path/restore-counts.txt"
cmp "$backup_dir/counts.txt" "$data_path/restore-counts.txt"

docker run --detach \
  --name "$app_container" \
  --network "$network" \
  --label dothomelab.restore-test=pinepods \
  --env SEARCH_API_URL=https://search.pinepods.online/api/search \
  --env PEOPLE_API_URL=https://people.pinepods.online \
  --env HOSTNAME=http://pinepods-restore.invalid \
  --env SERVER_URL=http://pinepods-restore.invalid \
  --env DB_TYPE=postgresql \
  --env "DB_HOST=$db_container" \
  --env DB_PORT=5432 \
  --env DB_USER=pinepods \
  --env "DB_PASSWORD=$db_password" \
  --env DB_NAME=pinepods \
  --env "VALKEY_HOST=$valkey_container" \
  --env VALKEY_PORT=6379 \
  --env VALKEY_PASSWORD=restore-test-only \
  --env FULLNAME="Restore Test Administrator" \
  --env USERNAME=restore-test \
  --env EMAIL=restore-test@invalid.example \
  --env PASSWORD=restore-test-only \
  --env PUID=1000 \
  --env PGID=1000 \
  --env TZ=UTC \
  --volume "$data_path/downloads:/opt/pinepods/downloads" \
  --volume "$data_path/app-backups:/opt/pinepods/backups" \
  madeofpendletonwool/pinepods:latest >/dev/null

health=""
for _ in {1..180}; do
  health="$(docker inspect --format '{{.State.Health.Status}}' "$app_container")"
  [[ "$health" == "healthy" ]] && break
  [[ "$health" == "unhealthy" ]] && {
    docker logs "$app_container" >&2
    exit 1
  }
  sleep 2
done
[[ "$health" == "healthy" ]] || {
  docker logs "$app_container" >&2
  exit 1
}

docker exec "$app_container" curl --fail --silent \
  http://127.0.0.1:8040/api/health >"$data_path/application-health.json"
docker exec "$app_container" curl --fail --silent \
  http://127.0.0.1:8040/api/pinepods_check >"$data_path/application-check.json"
query_counts "$db_container" >"$data_path/application-counts.txt"
cmp "$backup_dir/counts.txt" "$data_path/application-counts.txt"
sha256sum \
  "$data_path/restore-counts.txt" \
  "$data_path/application-counts.txt" \
  "$data_path/application-health.json" \
  "$data_path/application-check.json" \
  >"$data_path/RESTORE-TEST-SHA256SUMS"
chmod 0600 "$data_path"/*.txt "$data_path"/*.json "$data_path/RESTORE-TEST-SHA256SUMS"

docker stop "$app_container" "$valkey_container" "$db_container" >/dev/null
cleanup_pending=0
trap - EXIT INT TERM

printf 'PinePods isolated restore and application-readability test passed.\nnetwork=%s\ndata_path=%s\n' \
  "$network" "$data_path"
