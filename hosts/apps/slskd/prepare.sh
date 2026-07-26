#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly slskd_root="$appdata_root/slskd"
readonly music_root="/music"
readonly downloads_root="/slskd-downloads"
readonly network_name="slskd-droppedneedle"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

for path in "$music_root" "$downloads_root"; do
  source="$(findmnt -n -o SOURCE --target "$path")"
  [[ "$source" == vault/shared* ]] || {
    echo "$path is mounted from $source, expected vault/shared" >&2
    exit 1
  }
done

[[ "$(stat -c '%d' "$music_root")" == "$(stat -c '%d' "$downloads_root")" ]] || {
  echo "Music and slskd downloads are not on the same underlying filesystem" >&2
  exit 1
}

command -v setpriv >/dev/null || {
  echo "setpriv is required for mapped-user permission checks" >&2
  exit 1
}
setpriv --reuid=1000 --regid=1000 --clear-groups test -r "$music_root" || {
  echo "Apps UID/GID 1000:1000 cannot read $music_root" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 \
  "$slskd_root" \
  "$downloads_root" \
  "$downloads_root/complete" \
  "$downloads_root/incomplete"

docker network inspect "$network_name" >/dev/null 2>&1 ||
  docker network create --driver bridge "$network_name" >/dev/null

echo "slskd appdata, read-only share, downloads, and rollback network are prepared"
