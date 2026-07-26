#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker/pinepods"
readonly podcast_root="/podcasts/pinepods"

[[ -d "$podcast_root" ]] || {
  echo "PinePods podcast subtree is missing: $podcast_root" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$podcast_root")" == vault/shared* ]] || {
  echo "$podcast_root is not backed by vault/shared" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$appdata_root")" == rpool/appdata/docker ]] || {
  echo "$appdata_root is not backed by canonical appdata" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 \
  "$appdata_root" \
  "$appdata_root/backups" \
  "$appdata_root/backups/latest" \
  "$appdata_root/backups/previous" \
  "$appdata_root/restore-tests"
install -d -o 999 -g 999 -m 0700 "$appdata_root/postgres"

setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -r "$podcast_root"
setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -w "$podcast_root"

echo "PinePods appdata, PostgreSQL, dumps, restore tests, and episode subtree are prepared"
