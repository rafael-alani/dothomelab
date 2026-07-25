#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly -a library_roots=(
  /data/media/books
  /data/media/comics
  /data/media/mangas
)

[[ "$(findmnt -n -o SOURCE --target "$appdata_root")" == \
  "rpool/appdata/docker" ]] || {
  echo "$appdata_root is not mounted from rpool/appdata/docker" >&2
  exit 1
}

command -v setpriv >/dev/null || {
  echo "setpriv is required for mapped-user permission checks" >&2
  exit 1
}
for path in "${library_roots[@]}"; do
  [[ "$(findmnt -n -o SOURCE --target "$path")" == vault/shared* ]] || {
    echo "$path is not mounted from vault/shared" >&2
    exit 1
  }
  setpriv --reuid=1000 --regid=1000 --clear-groups test -r "$path" || {
    echo "Apps UID/GID 1000:1000 cannot read $path" >&2
    exit 1
  }
done

install -d -o 1000 -g 1000 -m 0750 "$appdata_root/kavita"
