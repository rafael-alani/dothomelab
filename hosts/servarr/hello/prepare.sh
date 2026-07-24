#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$(findmnt -n -o SOURCE -T /docker)" == "rpool/appdata/docker" ]] || {
  echo "/docker is not mounted from rpool/appdata/docker" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T /data)" == "vault/shared" ]] || {
  echo "/data is not mounted from vault/shared" >&2
  exit 1
}
[[ -c /dev/net/tun ]] || {
  echo "/dev/net/tun is not available" >&2
  exit 1
}

install -d -o 0 -g 0 -m 0755 \
  /docker/gluetun \
  /docker/servarr-portainer
install -d -o 1000 -g 1000 -m 0755 \
  /docker/qbittorrent \
  /docker/nzbget \
  /docker/prowlarr \
  /docker/sonarr \
  /docker/radarr \
  /docker/lidarr \
  /docker/readarr \
  /docker/bazarr \
  /docker/flaresolverr

echo "Servarr storage and TUN device are ready."
