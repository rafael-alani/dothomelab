#!/usr/bin/env bash
set -euo pipefail

appdata_root="/srv/appdata/docker"
actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"

if [[ "$actual_source" != "rpool/appdata/docker" ]]; then
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
fi

install -d -m 0755 \
  "$appdata_root/homarr/db" \
  "$appdata_root/pihole/etc-pihole" \
  "$appdata_root/pihole/etc-dnsmasq.d"
