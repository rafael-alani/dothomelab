#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
backup_root=/srv/appdata/docker/blog-observability/backups
[[ -d "$backup_root" ]] || { echo 'Blog backup directory is missing' >&2; exit 1; }
target="$(mktemp -d "$backup_root/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
docker exec blog-umami-db pg_dump --username=umami --dbname=umami --format=custom >"$target/umami.dump"
docker exec -i blog-umami-db pg_restore --list <"$target/umami.dump" >/dev/null
(cd "$target" && sha256sum umami.dump >SHA256SUMS)
ln -s "$(basename "$target")" "$backup_root/latest.next"
mv -Tf "$backup_root/latest.next" "$backup_root/latest"
echo 'Blog Umami logical backup created and archive table of contents checked; restore not implied'
