#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/docker/soularr"
readonly aurral_data="/docker/aurral/data"
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
setpriv --reuid=1000 --regid=1000 --clear-groups test -r "$aurral_data/aurral.db"
setpriv --reuid=1000 --regid=1000 --clear-groups test -w "$downloads"

echo "Soularr appdata, read-only Aurral history, and slskd-download view are prepared"
