#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly bar_root="$appdata_root/bar-assistant"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

install -d -m 0750 "$bar_root"
install -d -o 33 -g 33 -m 0750 "$bar_root/data"
install -d -o 1000 -g 1000 -m 0750 "$bar_root/meilisearch"
install -d -o 999 -g 999 -m 0750 "$bar_root/redis"
