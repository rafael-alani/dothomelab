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
install -d -o 10001 -g 10001 -m 0700 \
  "$paperless_root/gpt" \
  "$paperless_root/gpt/prompts" \
  "$paperless_root/gpt/config" \
  "$paperless_root/gpt/db"

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
