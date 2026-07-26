#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_root="/srv/appdata/docker/pinepods/backups"
readonly latest="$backup_root/latest"
readonly previous="$backup_root/previous"
temporary="$(mktemp -d "$backup_root/.database-backup.XXXXXX")"
trap 'rm -r -- "$temporary"' EXIT

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    pinepods-db
)"
[[ "$state" == "running healthy" ]] || {
  echo "PinePods PostgreSQL is not healthy: $state" >&2
  exit 1
}

install -d -m 0700 "$latest" "$previous"
docker exec pinepods-db pg_dump \
  --format=custom \
  --dbname=pinepods \
  --username=pinepods \
  >"$temporary/pinepods.dump"
docker exec pinepods-db pg_dumpall \
  --roles-only \
  --username=pinepods |
  gzip -1 >"$temporary/roles.sql.gz"
docker exec pinepods-db psql \
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
  " >"$temporary/counts.txt"
docker exec pinepods-db psql \
  --dbname=pinepods \
  --username=pinepods \
  --no-align \
  --tuples-only \
  --command="
    SELECT 'server_version=' || current_setting('server_version')
    UNION ALL
    SELECT 'database_size=' || pg_database_size(current_database())::text
    ORDER BY 1
  " >"$temporary/database.txt"

(
  cd "$temporary"
  sha256sum pinepods.dump roles.sql.gz counts.txt database.txt >SHA256SUMS
)
chmod 0600 "$temporary"/*

for file in pinepods.dump roles.sql.gz counts.txt database.txt SHA256SUMS; do
  if [[ -s "$latest/$file" ]]; then
    install -m 0600 "$latest/$file" "$previous/$file"
  fi
  install -m 0600 "$temporary/$file" "$latest/$file"
done

echo "$latest"
