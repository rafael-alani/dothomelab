#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly loki_root="$appdata_root/loki"
readonly observability_network="dothomelab-observability"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

install -d -o 10001 -g 10001 -m 0750 "$loki_root"
install -d -o 10001 -g 10001 -m 0750 \
  "$loki_root/chunks" \
  "$loki_root/compactor" \
  "$loki_root/rules"

if ! docker network inspect "$observability_network" >/dev/null 2>&1; then
  docker network create \
    --driver bridge \
    --label dothomelab.managed=true \
    "$observability_network" >/dev/null
fi
