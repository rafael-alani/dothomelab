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
