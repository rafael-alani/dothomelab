#!/usr/bin/env bash
set -Eeuo pipefail

readonly source_dir="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd
)"
readonly output="${1:?usage: build-epub.sh OUTPUT.epub}"

temporary="$(mktemp -d)"
trap 'rm -rf -- "$temporary"' EXIT
cp -R "$source_dir/META-INF" "$source_dir/OEBPS" "$temporary/"
cp "$source_dir/mimetype" "$temporary/mimetype"
(
  cd "$temporary"
  zip -X -0 "$output" mimetype >/dev/null
  zip -X -r "$output" META-INF OEBPS >/dev/null
)
printf 'Built user-owned Storyteller fixture: %s\n' "$output"
