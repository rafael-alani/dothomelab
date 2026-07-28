#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

[[ "$(findmnt -n -o SOURCE -T /docker)" == "rpool/appdata/docker" ]] ||
  fail "/docker is not backed by rpool/appdata/docker"
[[ "$(findmnt -n -o SOURCE -T /data/media/audiobooks)" == "vault/shared"* ]] ||
  fail "canonical audiobooks are not backed by vault/shared"
[[ "$(findmnt -n -o SOURCE -T /data/torrents)" == "vault/shared"* ]] ||
  fail "torrent downloads are not backed by vault/shared"
[[ "$(findmnt -n -o SOURCE -T /data/usernet)" == "vault/shared"* ]] ||
  fail "Usenet downloads are not backed by vault/shared"

install -d -o 1000 -g 1000 -m 0750 \
  /docker/listenarr \
  /docker/listenarr/backups \
  /docker/listenarr/database
install -d -o 1000 -g 996 -m 0775 \
  /data/torrents/completed \
  /data/torrents/completed/listenarr

echo "Listenarr appdata and dedicated download path prepared"
