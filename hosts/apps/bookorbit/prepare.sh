#!/usr/bin/env bash
set -Eeuo pipefail

readonly root="/srv/appdata/docker/bookorbit"

install -d -o 1000 -g 1000 -m 0750 \
  "$root" \
  "$root/app" \
  "$root/app/book-bucket" \
  "$root/app/book-dock" \
  "$root/app/covers"
install -d -o 999 -g 999 -m 0700 "$root/postgres"
install -d -o 1000 -g 1000 -m 0700 \
  "$root/backups" \
  "$root/backups/latest" \
  "$root/backups/previous" \
  "$root/restore-tests"

for path in \
  /data/media/books/ebooks \
  /data/media/books/pdfs \
  /data/media/comics \
  /data/media/mangas; do
  [[ -d "$path" ]] || {
    echo "Required BookOrbit library path is missing: $path" >&2
    exit 1
  }
done

echo "BookOrbit appdata, PostgreSQL, and read-only library paths are prepared"
