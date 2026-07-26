#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly audiobooks_root="/srv/appdata/docker/audiobookshelf/libraries/audiobooks"

[[ "$(findmnt -n -o SOURCE --target "$appdata_root")" == \
  "rpool/appdata/docker" ]] || {
  echo "$appdata_root is not mounted from rpool/appdata/docker" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE --target "$audiobooks_root")" == \
  "vault/shared["*"]" ||
  "$(findmnt -n -o SOURCE --target "$audiobooks_root")" == \
  "/dev/sdb1["*"]" ]] || {
  echo "$audiobooks_root is not a narrow mount from vault/shared" >&2
  exit 1
}
command -v setpriv >/dev/null || {
  echo "setpriv is required for mapped-user permission checks" >&2
  exit 1
}
setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -r "$audiobooks_root" || {
  echo "Apps UID/GID 1000:1000 cannot read $audiobooks_root" >&2
  exit 1
}
if ! setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -w "$audiobooks_root"; then
  echo "Apps UID/GID 1000:1000 cannot write $audiobooks_root" >&2
  exit 1
fi
install -d -o 1000 -g 1000 -m 0750 \
  "$appdata_root/audiobookshelf" \
  "$appdata_root/audiobookshelf/config" \
  "$appdata_root/audiobookshelf/metadata"
