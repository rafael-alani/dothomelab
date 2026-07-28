#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/docker/cross-seed"
readonly link_dir="/data/torrents/cross-seed-links"

[[ "$(findmnt -n -o SOURCE -T /docker)" == "rpool/appdata/docker" ]] || {
  echo "/docker is not canonical appdata" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T /data)" == "vault/shared" ]] || {
  echo "/data is not canonical shared storage" >&2
  exit 1
}
[[ -d /data/torrents && ! -L /data/torrents ]] || {
  echo "/data/torrents is missing or is a symlink" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 "$appdata"
install -d -o 1000 -g 1000 -m 0750 "$link_dir"

[[ "$(stat -c %d /data/torrents)" == "$(stat -c %d "$link_dir")" ]] || {
  echo "cross-seed link directory is not on the qBittorrent data filesystem" >&2
  exit 1
}

echo "cross-seed canonical appdata and hardlink directory are prepared"
