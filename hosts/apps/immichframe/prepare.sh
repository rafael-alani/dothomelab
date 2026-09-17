#!/usr/bin/env bash
set -euo pipefail

readonly appdata_root="/srv/appdata/docker"
actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"

if [[ "$actual_source" != "rpool/appdata/docker" ]]; then
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
fi

# The upstream image runs as UID 1000 and now stores settings in SQLite.
# Change only this directory, never recursively rewrite restored appdata.
install -d -o 1000 -g 1000 -m 0700 "$appdata_root/immichframe/config"
