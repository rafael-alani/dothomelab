#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/docker/cleanuparr"

[[ "$(findmnt -n -o SOURCE -T /docker)" == "rpool/appdata/docker" ]] || {
  echo "/docker is not canonical appdata" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 "$appdata"

echo "Cleanuparr canonical appdata is prepared"
