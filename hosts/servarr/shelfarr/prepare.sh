#!/usr/bin/env bash
set -Eeuo pipefail

readonly root="/docker/shelfarr"

install -d -o 1000 -g 1000 -m 0750 \
  "$root" \
  "$root/data" \
  "$root/libation" \
  "$root/libation/books"
install -d -o 1000 -g 1000 -m 0700 \
  "$root/libation/config" \
  "$root/libation/control"

for path in \
  /data/media/books/ebooks \
  /data/media/audiobooks \
  /data/torrents \
  /data/usernet; do
  [[ -d "$path" ]] || {
    echo "Required Shelfarr path is missing: $path" >&2
    exit 1
  }
done

echo "Shelfarr appdata and canonical media paths are prepared"
