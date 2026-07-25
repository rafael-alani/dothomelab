#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly downloads="/downloads"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

download_source="$(findmnt -n -o SOURCE --target "$downloads")"
[[ "$download_source" == vault/shared* ]] || {
  echo "$downloads is mounted from $download_source, expected vault/shared" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 "$appdata_root/yt-dlp-web-ui"
install -d -o 1000 -g 1000 -m 0750 "$downloads"
