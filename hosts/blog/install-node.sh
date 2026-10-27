#!/usr/bin/env bash
# Native toolchain shared by the publisher and static builders.
set -euo pipefail
if [[ -x /usr/local/bin/node ]] && [[ "$(/usr/local/bin/node -p 'process.versions.node.split(".")[0]')" == 24 ]]; then
  exit 0
fi
version=v24.14.0
archive="node-$version-linux-x64.tar.xz"
work="$(mktemp -d /run/blog-node.XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
curl -fsS "https://nodejs.org/dist/$version/$archive" -o "$work/$archive"
curl -fsS "https://nodejs.org/dist/$version/SHASUMS256.txt" -o "$work/SHASUMS256.txt"
(cd "$work" && grep " $archive\$" SHASUMS256.txt | sha256sum -c -)
install -d /opt/node
# This version directory is immutable; existing other versions remain available.
if [[ ! -d "/opt/node/node-$version-linux-x64" ]]; then
  tar -xJf "$work/$archive" -C /opt/node
fi
for binary in node npm npx; do
  ln -sfn "/opt/node/node-$version-linux-x64/bin/$binary" "/usr/local/bin/$binary"
done
