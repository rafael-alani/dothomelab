#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly snapotter_root="$appdata_root/snapotter"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

install -d -m 0750 "$snapotter_root"
install -d -o 999 -g 999 -m 0750 \
  "$snapotter_root/data" \
  "$snapotter_root/workspace" \
  "$snapotter_root/redis"
install -d -o 70 -g 70 -m 0700 "$snapotter_root/postgres"
install -d -m 0700 \
  "$snapotter_root/backups" \
  "$snapotter_root/restore-tests"
