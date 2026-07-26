#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/srv/appdata/docker/music-metadata"
readonly music="/music"
readonly soularr_state="/srv/appdata/docker/soularr"

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker)" == "rpool/appdata/docker" ]] || {
  echo "/srv/appdata/docker is not canonical appdata" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$soularr_state")" == "rpool/appdata/docker" ]] || {
  echo "$soularr_state is not on canonical appdata" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$music")" == vault/shared* ]] || {
  echo "$music is not the narrow vault/shared music bind" >&2
  exit 1
}
[[ ",$(findmnt -n -o OPTIONS -T "$music")," != *,ro,* ]] || {
  echo "$music must be read-write only for the metadata writer in CT112" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 \
  "$appdata" \
  "$appdata/work" \
  "$appdata/reports"
[[ "$(findmnt -n -o SOURCE -T "$appdata")" == "rpool/appdata/docker" ]] || {
  echo "$appdata is not on canonical appdata after creation" >&2
  exit 1
}
touch "$soularr_state/.dothomelab-job.lock"
chown 1000:1000 "$soularr_state/.dothomelab-job.lock"
chmod 0640 "$soularr_state/.dothomelab-job.lock"

setpriv --reuid=1000 --regid=996 --clear-groups test -r "$music"
setpriv --reuid=1000 --regid=996 --clear-groups test -w "$music"
setpriv --reuid=1000 --regid=996 --clear-groups test -w "$appdata"
setpriv --reuid=1000 --regid=996 --clear-groups test -w \
  "$soularr_state/.dothomelab-job.lock"

echo "Music metadata appdata, shared acquisition lock, and narrow music writer are prepared"
