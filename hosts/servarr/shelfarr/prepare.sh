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
  "$root/libation/control" \
  "$root/staging" \
  "$root/staging/ebooks" \
  "$root/staging/ebooks/common" \
  "$root/staging/ebooks/uploads" \
  "$root/staging/audiobooks" \
  "$root/staging/audiobooks/common" \
  "$root/staging/audiobooks/uploads" \
  "$root/staging/audiobooks/zip-uploads"

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
