#!/usr/bin/env bash
set -euo pipefail

readonly appdata_root="/srv/appdata/docker"
actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"

if [[ "$actual_source" != "rpool/appdata/docker" ]]; then
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
fi

# The default deployment is environment-driven. Keep the upstream-recommended
# Config mount available for future Settings.yml or custom assets.
install -d -m 0755 "$appdata_root/immichframe/config"
