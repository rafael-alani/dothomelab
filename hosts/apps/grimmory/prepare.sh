#!/usr/bin/env bash
set -Eeuo pipefail

readonly root="/srv/appdata/docker/grimmory"

[[ "$(findmnt -n -o SOURCE -T "$root")" == "rpool/appdata/docker" ]] || {
  echo "$root is not on canonical appdata" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 \
  "$root" \
  "$root/data" \
  "$root/backups" \
  "$root/backups/latest" \
  "$root/backups/previous" \
  "$root/restore-tests"
install -d -o 1000 -g 1000 -m 0700 "$root/mariadb"

for path in "$root/libraries/ebooks" "$root/libraries/audiobooks"; do
  source="$(findmnt -n -o SOURCE -T "$path")"
  [[ -d "$path" &&
    ( "$source" == "vault/shared["*"]" || "$source" == "/dev/sdb1["*"]" ) ]] || {
    echo "Required Grimmory narrow library bind is missing: $path" >&2
    exit 1
  }
done

echo "Grimmory appdata, MariaDB, backups, and narrow canonical-library binds are prepared"
