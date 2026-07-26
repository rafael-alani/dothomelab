#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/docker/soularr"
readonly downloads="/data/media/slskd"

[[ "$(findmnt -n -o SOURCE -T "$appdata")" == "rpool/appdata/docker" ]] || {
  echo "$appdata is not on canonical appdata through CT102 /docker" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$downloads")" == vault/shared* ]] || {
  echo "$downloads is not backed by vault/shared" >&2
  exit 1
}
[[ ",$(findmnt -n -o OPTIONS -T "$downloads")," != *,ro,* ]] || {
  echo "$downloads is unexpectedly read-only in CT102" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 "$appdata"
install -d -o 1000 -g 1000 -m 0750 \
  "$downloads/complete" "$downloads/incomplete"
setpriv --reuid=1000 --regid=1000 --clear-groups test -w "$appdata"
setpriv --reuid=1000 --regid=1000 --clear-groups test -w "$downloads"

echo "Soularr appdata and the existing CT102 slskd-download view are prepared"
