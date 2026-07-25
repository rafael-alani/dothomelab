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

install -d -o 1000 -g 1000 -m 0700 \
  /data/temp/shelfarr-staging \
  /data/temp/shelfarr-staging/ebooks \
  /data/temp/shelfarr-staging/ebooks/common \
  /data/temp/shelfarr-staging/ebooks/uploads \
  /data/temp/shelfarr-staging/audiobooks \
  /data/temp/shelfarr-staging/audiobooks/common \
  /data/temp/shelfarr-staging/audiobooks/uploads \
  /data/temp/shelfarr-staging/audiobooks/zip-uploads

[[ "$(findmnt -n -o SOURCE -T /data/temp/shelfarr-staging)" == vault/shared* ]] || {
  echo "Shelfarr staging is not on the shared library filesystem" >&2
  exit 1
}

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
