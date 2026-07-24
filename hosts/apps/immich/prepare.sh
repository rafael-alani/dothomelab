#!/usr/bin/env bash
set -euo pipefail

appdata_root="/srv/appdata/docker"
upload_path="$appdata_root/immich/upload"
database_path="$appdata_root/immich/postgres"
model_cache_path="$appdata_root/immich/model-cache"
backup_path="$appdata_root/immich/backups"
restore_test_path="$appdata_root/immich/restore-tests"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

[[ -d "$upload_path" ]] || {
  echo "Missing verified Immich upload copy: $upload_path" >&2
  exit 1
}
[[ -d "$database_path" ]] || {
  echo "Missing verified Immich PostgreSQL copy: $database_path" >&2
  exit 1
}
[[ "$(<"$database_path/PG_VERSION")" == "14" ]] || {
  echo "Expected PostgreSQL 14 data at $database_path" >&2
  exit 1
}
[[ -d /data/media/photos ]] || {
  echo "Missing external Immich library: /data/media/photos" >&2
  exit 1
}

install -d -o 0 -g 0 -m 0755 "$model_cache_path"
install -d -o 0 -g 0 -m 0700 "$backup_path" "$restore_test_path"

pid_file="$database_path/postmaster.pid"
if [[ -e "$pid_file" ]]; then
  running_mount="$(
    docker inspect \
      --format '{{if .State.Running}}{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Source}}{{end}}{{end}}{{end}}' \
      immich_migration_postgres 2>/dev/null || true
  )"
  if [[ -n "$running_mount" ]]; then
    [[ "$running_mount" == "$database_path" ]] || {
      echo "Running Immich PostgreSQL uses unexpected data path $running_mount" >&2
      exit 1
    }
  else
    runtime_backup="$backup_path/recovered-runtime"
    install -d -o 0 -g 0 -m 0700 "$runtime_backup"
    mv "$pid_file" \
      "$runtime_backup/postmaster.pid.$(date --utc +%Y%m%dT%H%M%SZ).$$"
    echo "Archived stale Immich PostgreSQL PID marker from the recovered snapshot"
  fi
fi

echo "Immich PostgreSQL 14 and application recovery paths are ready"
