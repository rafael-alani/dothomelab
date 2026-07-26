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

ebook_path="$root/libraries/ebooks"
ebook_source="$(findmnt -n -o SOURCE -T "$ebook_path")"
[[ -d "$ebook_path" &&
  ( "$ebook_source" == "vault/shared["*"]" ||
    "$ebook_source" == "/dev/sdb1["*"]" ) ]] || {
  echo "Required Grimmory narrow ebook bind is missing: $ebook_path" >&2
  exit 1
}
setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -w "$ebook_path" || {
  echo "Grimmory cannot write the canonical ebook bind" >&2
  exit 1
}
setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -r /data/media/audiobooks || {
  echo "Grimmory cannot read the canonical audiobook tree" >&2
  exit 1
}
if setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -w /data/media/audiobooks; then
  echo "Grimmory must not write the canonical audiobook tree" >&2
  exit 1
fi

echo "Grimmory appdata, MariaDB, writable ebooks, and read-only audiobooks are prepared"
