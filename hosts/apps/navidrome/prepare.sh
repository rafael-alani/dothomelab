#!/usr/bin/env bash
set -Eeuo pipefail

readonly root="/srv/appdata/docker/navidrome"
readonly data="$root/data"
readonly music="/data/media/music"
readonly flows="/srv/appdata/docker/aurral/flows"

[[ "$(findmnt -n -o SOURCE -T "$root")" == "rpool/appdata/docker" ]] || {
  echo "$root is not on canonical appdata" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$flows")" == *"aurral-flows]" ]] || {
  echo "$flows is not the narrow vault/shared flow bind" >&2
  exit 1
}
[[ ",$(findmnt -n -o OPTIONS -T "$music")," == *,ro,* ]] || {
  echo "$music must remain read-only in CT112" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 "$data"
setpriv --reuid=1000 --regid=1000 --clear-groups test -r "$music"
setpriv --reuid=1000 --regid=1000 --clear-groups test -r "$flows"

echo "Navidrome appdata and both read-only libraries are prepared"
