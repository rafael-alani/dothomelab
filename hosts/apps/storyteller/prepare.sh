#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata="/srv/appdata/docker/storyteller"
readonly shared="/storyteller"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

[[ "$(findmnt -n -o SOURCE -T "$appdata")" == "rpool/appdata/docker" ]] ||
  fail "$appdata is not on canonical appdata"
[[ "$(findmnt -n -o SOURCE -T "$shared")" == vault/shared* ]] ||
  fail "$shared is not the narrow vault/shared Storyteller bind"
[[ "$(findmnt -n -o OPTIONS -T /data)" == *ro* ]] ||
  fail "CT112 broad /data mount is not read-only"

for path in /data/media/books/ebooks /data/media/audiobooks; do
  setpriv --reuid=1000 --regid=1000 --clear-groups test -r "$path" ||
    fail "Storyteller reconciler cannot read $path"
  if setpriv --reuid=1000 --regid=1000 --clear-groups test -w "$path"; then
    fail "Storyteller canonical input is writable: $path"
  fi
done

install -d -o 1000 -g 1000 -m 0750 \
  "$appdata" \
  "$appdata/database" \
  "$appdata/reconciler" \
  "$appdata/reconciler/backups" \
  "$appdata/reconciler/backups/latest" \
  "$appdata/reconciler/backups/previous" \
  "$appdata/secrets" \
  "$appdata/watcher-snapshots"

install -d -o 1000 -g 1000 -m 0750 \
  "$shared/inbox/.staging" \
  "$shared/library"

setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -w "$shared/inbox" ||
  fail "Apps UID/GID 1000:1000 cannot write the Storyteller inbox"
setpriv --reuid=1000 --regid=1000 --clear-groups \
  test -w "$shared/library" ||
  fail "Apps UID/GID 1000:1000 cannot write the Storyteller library"

printf 'Storyteller appdata and narrow shared paths are prepared\n'
