#!/usr/bin/env bash
set -euo pipefail

appdata_root="/srv/appdata/docker"
actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"

if [[ "$actual_source" != "rpool/appdata/docker" ]]; then
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
fi

install -d -o 101 -g 101 -m 0750 "$appdata_root/zotero-webdav"
