#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly paperless_root="$appdata_root/paperless"
readonly paperless_network="dothomelab-paperless"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

install -d -m 0750 "$paperless_root"
install -d -o 1000 -g 1000 -m 0750 \
  "$paperless_root/data" \
  "$paperless_root/media" \
  "$paperless_root/media/trash" \
  "$paperless_root/export" \
  "$paperless_root/consume"
install -d -o 999 -g 999 -m 0700 \
  "$paperless_root/postgres" \
  "$paperless_root/valkey"
install -d -m 0700 \
  "$paperless_root/backups" \
  "$paperless_root/restore-tests"

network_driver="$(
  docker network inspect --format '{{.Driver}}' "$paperless_network" 2>/dev/null ||
    true
)"
if [[ -z "$network_driver" ]]; then
  docker network create \
    --driver bridge \
    --label dothomelab.managed=true \
    "$paperless_network" >/dev/null
elif [[ "$network_driver" != "bridge" ]]; then
  echo "$paperless_network uses driver $network_driver, expected bridge" >&2
  exit 1
fi
