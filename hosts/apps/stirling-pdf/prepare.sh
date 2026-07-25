#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly stirling_root="$appdata_root/stirling-pdf"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

install -d -m 0750 "$stirling_root"
install -d -o 1000 -g 1000 -m 0750 \
  "$stirling_root/configs" \
  "$stirling_root/custom-files" \
  "$stirling_root/logs" \
  "$stirling_root/pipeline" \
  "$stirling_root/tessdata"
