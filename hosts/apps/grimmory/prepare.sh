#!/usr/bin/env bash
set -Eeuo pipefail

readonly root="/srv/appdata/docker/grimmory"

[[ "$(findmnt -n -o SOURCE -T "$root")" == "rpool/appdata/docker" ]] || {
  echo "$root is not on canonical appdata" >&2
  exit 1
}
[[ "$(stat -c '%u:%g %a' "$root")" == "1000:1000 750" ]] || {
  echo "$root ownership or mode drifted" >&2
  exit 1
}

setpriv --reuid=1000 --regid=1000 --clear-groups \
  install -d -m 0750 \
  "$root/data" \
  "$root/backups" \
  "$root/backups/latest" \
  "$root/backups/previous" \
  "$root/restore-tests"
setpriv --reuid=1000 --regid=1000 --clear-groups \
  install -d -m 0700 "$root/mariadb"

for path in "$root/libraries/ebooks" "$root/libraries/audiobooks"; do
  source="$(findmnt -n -o SOURCE -T "$path")"
  [[ -d "$path" &&
    ( "$source" == "vault/shared["*"]" || "$source" == "/dev/sdb1["*"]" ) ]] || {
    echo "Required Grimmory narrow library bind is missing: $path" >&2
    exit 1
  }
done

echo "Grimmory appdata, MariaDB, backups, and narrow canonical-library binds are prepared"
