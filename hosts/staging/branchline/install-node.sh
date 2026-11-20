#!/usr/bin/env bash
set -Eeuo pipefail
export PATH=/usr/local/bin:/usr/bin:/bin
# Shared pinned runtime for the preview runner and fresh development VM.
version=24.22.3
digest=4f2b175a6d53a5c617a80dba2676238a0688cef28c6da4eba35c7d844e66fcfb
target="/opt/node-v${version}-linux-x64"
if [[ ! -x "$target/bin/node" ]]; then
  archive="$(mktemp --suffix=.tar.xz)"
  trap 'rm -f -- "$archive"' EXIT
  curl --fail --silent --show-error --location "https://nodejs.org/dist/v${version}/node-v${version}-linux-x64.tar.xz" -o "$archive"
  printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status
  tar -xJf "$archive" -C /opt
fi
for executable in node npm npx corepack; do
  [[ ! -e "$target/bin/$executable" ]] || ln -sfn "$target/bin/$executable" "/usr/local/bin/$executable"
done
node --version
