#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_root="/srv/appdata/docker/grimmory/backups"
readonly latest="$backup_root/latest"
readonly previous="$backup_root/previous"
temporary="$(mktemp -d "$backup_root/.database-backup.XXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT

state="$(docker inspect --format \
  '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
  grimmory-db)"
[[ "$state" == "running healthy" ]] || {
  echo "Grimmory MariaDB is not healthy: $state" >&2
  exit 1
}

db_password="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' grimmory-db |
    sed -n 's/^MYSQL_PASSWORD=//p'
)"
[[ -n "$db_password" ]]

install -d -m 0700 "$latest" "$previous"
docker exec grimmory-db mariadb-dump \
  --user=grimmory \
  --password="$db_password" \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  grimmory |
  gzip -1 >"$temporary/grimmory.sql.gz"
while IFS= read -r table_name; do
  row_count="$(
    docker exec grimmory-db mariadb \
      --user=grimmory \
      --password="$db_password" \
      --batch \
      --skip-column-names \
      --execute="SELECT COUNT(*) FROM \`$table_name\`;" \
      grimmory
  )"
  printf '%s=%s\n' "$table_name" "$row_count"
done < <(
  docker exec grimmory-db mariadb \
    --user=grimmory \
    --password="$db_password" \
    --batch \
    --skip-column-names \
    --execute='
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = "grimmory"
      ORDER BY table_name;
    ' grimmory
) >"$temporary/counts.txt"

(
  cd "$temporary"
  sha256sum grimmory.sql.gz counts.txt >SHA256SUMS
)
chmod 0600 "$temporary"/*

for file in grimmory.sql.gz counts.txt SHA256SUMS; do
  if [[ -s "$latest/$file" ]]; then
    install -m 0600 "$latest/$file" "$previous/$file"
  fi
  install -m 0600 "$temporary/$file" "$latest/$file"
done

echo "$latest"
