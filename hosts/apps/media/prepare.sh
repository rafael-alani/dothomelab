#!/usr/bin/env bash
set -euo pipefail

appdata_root="/srv/appdata/docker"
actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"

if [[ "$actual_source" != "rpool/appdata/docker" ]]; then
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
fi

install -d -m 0755 \
  "$appdata_root/jellyfin/config" \
  "$appdata_root/jellyfin/cache" \
  "$appdata_root/jellystat/backup-data"

# The upstream Seerr image runs as UID/GID 1000.
install -d -o 1000 -g 1000 -m 0755 "$appdata_root/seerr/config"

# PostgreSQL 18 stores its versioned cluster below /var/lib/postgresql.
install -d -o 999 -g 999 -m 0700 "$appdata_root/jellystat/postgres"

pid_file="$appdata_root/jellystat/postgres/18/docker/postmaster.pid"
if [[ -e "$pid_file" ]]; then
  running_mount="$(
    docker inspect \
      --format '{{if .State.Running}}{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql"}}{{.Source}}{{end}}{{end}}{{end}}' \
      jellystat-db 2>/dev/null || true
  )"
  if [[ -n "$running_mount" ]]; then
    [[ "$running_mount" == "$appdata_root/jellystat/postgres" ]] || {
      echo "Running Jellystat PostgreSQL uses unexpected data path $running_mount" >&2
      exit 1
    }
  else
    runtime_backup="$appdata_root/jellystat/recovered-runtime"
    install -d -o 0 -g 0 -m 0700 "$runtime_backup"
    mv "$pid_file" \
      "$runtime_backup/postmaster.pid.$(date --utc +%Y%m%dT%H%M%SZ).$$"
    echo "Archived stale Jellystat PostgreSQL PID marker from the recovered snapshot"
  fi
fi
