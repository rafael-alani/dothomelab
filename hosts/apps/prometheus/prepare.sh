#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly prometheus_root="$appdata_root/prometheus"
readonly observability_network="dothomelab-observability"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

install -d -o 65534 -g 65534 -m 0750 "$prometheus_root"

if ! docker network inspect "$observability_network" >/dev/null 2>&1; then
  docker network create \
    --driver bridge \
    --label dothomelab.managed=true \
    "$observability_network" >/dev/null
fi
