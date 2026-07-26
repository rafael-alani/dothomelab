#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/srv/appdata/docker/aurral"
readonly data="$appdata/data"
readonly flows="$appdata/flows"
readonly music="/data/media/music"

[[ "$(findmnt -n -o SOURCE -T "$appdata")" == "rpool/appdata/docker" ]] || {
  echo "$appdata is not on canonical appdata" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$flows")" == *"aurral-flows]" ]] || {
  echo "$flows is not the narrow vault/shared flow bind" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$music")" == vault/shared* ]] || {
  echo "$music is not backed by vault/shared" >&2
  exit 1
}
[[ ",$(findmnt -n -o OPTIONS -T "$music")," == *,ro,* ]] || {
  echo "$music must remain read-only in CT112" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 "$data"
setpriv --reuid=1000 --regid=1000 --clear-groups test -r "$music"
setpriv --reuid=1000 --regid=1000 --clear-groups test -w "$flows"

echo "Aurral appdata, read-only Lidarr library view, and separate flow root are prepared"
