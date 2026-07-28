#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ -z "$1" ] || [ "$1" = "/" ]; then
    echo "usage: $0 DESTINATION_DIRECTORY" >&2
    exit 2
fi

destination=$1
mkdir -p "$destination"

hifimule_file="$destination/HifiMule_aarch64.app.tar.gz"
echolist_file="$destination/echolist-macos-arm64"

curl --fail --location --proto '=https' --tlsv1.2 \
    --output "$hifimule_file" \
    "https://github.com/HifiMule/HifiMule/releases/download/v0.13.0/HifiMule_aarch64.app.tar.gz"
curl --fail --location --proto '=https' --tlsv1.2 \
    --output "$echolist_file" \
    "https://github.com/purpleturtle21/echo-list/releases/download/v0.2.0/echolist-macos-arm64"

actual_hifimule=$(shasum -a 256 "$hifimule_file" | awk '{print $1}')
actual_echolist=$(shasum -a 256 "$echolist_file" | awk '{print $1}')

expected_hifimule="d554ba4a0629f17504390a7a2cdaaa46ed384e91e929a4796401d7e532d466d3"
expected_echolist="19bdff0aca4d211536968911db80b8176f6bd910d2647b1a7b5423873b1abb94"

if [ "$actual_hifimule" != "$expected_hifimule" ]; then
    echo "HifiMule checksum mismatch; do not install $hifimule_file" >&2
    exit 1
fi
if [ "$actual_echolist" != "$expected_echolist" ]; then
    echo "EchoList checksum mismatch; do not run $echolist_file" >&2
    exit 1
fi

chmod 0755 "$echolist_file"
echo "verified HifiMule v0.13.0 and EchoList v0.2.0 in $destination"
echo "Nothing was installed or executed."
