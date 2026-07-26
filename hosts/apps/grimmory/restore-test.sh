#!/usr/bin/env bash
set -Eeuo pipefail

readonly backup_dir="${1:-/srv/appdata/docker/grimmory/backups/latest}"
[[ -s "$backup_dir/grimmory.sql.gz" && -s "$backup_dir/SHA256SUMS" ]] || {
  echo "Grimmory backup is incomplete: $backup_dir" >&2
  exit 2
}

(
  cd "$backup_dir"
  sha256sum --check SHA256SUMS
)

db_password="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' grimmory-db |
    sed -n 's/^MYSQL_PASSWORD=//p'
)"
root_password="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' grimmory-db |
    sed -n 's/^MYSQL_ROOT_PASSWORD=//p'
)"
[[ -n "$db_password" && -n "$root_password" ]]

timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
container="grimmory_restore_test_${timestamp,,}"
container="${container//[^a-z0-9_.-]/_}"
data_path="/srv/appdata/docker/grimmory/restore-tests/$timestamp"
install -d -o 1000 -g 1000 -m 0700 "$data_path"

docker run --detach \
  --name "$container" \
  --network none \
  --label dothomelab.restore-test=grimmory \
  --env PUID=1000 \
  --env PGID=1000 \
  --env TZ=Etc/UTC \
  --env "MYSQL_ROOT_PASSWORD=$root_password" \
  --env MYSQL_DATABASE=grimmory \
  --env MYSQL_USER=grimmory \
  --env "MYSQL_PASSWORD=$db_password" \
  --volume "$data_path:/config" \
  lscr.io/linuxserver/mariadb:11.4.8 >/dev/null

cleanup_pending=1
cleanup() {
  if [[ "$cleanup_pending" -eq 1 ]]; then
    docker stop "$container" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

ready_streak=0
for _ in {1..180}; do
  if docker exec "$container" mariadb-admin ping -h localhost >/dev/null 2>&1; then
    ready_streak=$((ready_streak + 1))
    [[ "$ready_streak" -ge 5 ]] && break
  else
    ready_streak=0
  fi
  sleep 1
done
[[ "$ready_streak" -ge 5 ]] || {
  docker logs "$container" >&2
  exit 1
}

gzip -dc "$backup_dir/grimmory.sql.gz" |
  docker exec --interactive "$container" mariadb \
    --user=grimmory \
    --password="$db_password" \
    grimmory

while IFS= read -r table_name; do
  row_count="$(
    docker exec "$container" mariadb \
      --user=grimmory \
      --password="$db_password" \
      --batch \
      --skip-column-names \
      --execute="SELECT COUNT(*) FROM \`$table_name\`;" \
      grimmory
  )"
  printf '%s=%s\n' "$table_name" "$row_count"
done < <(
  docker exec "$container" mariadb \
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
) >"$data_path/restore-test-counts.txt"

cmp "$backup_dir/counts.txt" "$data_path/restore-test-counts.txt"
sha256sum "$data_path/restore-test-counts.txt" \
  >"$data_path/RESTORE-TEST-SHA256SUMS"
chmod 0600 \
  "$data_path/restore-test-counts.txt" \
  "$data_path/RESTORE-TEST-SHA256SUMS"

docker stop "$container" >/dev/null
cleanup_pending=0
trap - EXIT INT TERM

printf 'Grimmory restore test passed.\ncontainer=%s\ndata_path=%s\n' \
  "$container" "$data_path"
