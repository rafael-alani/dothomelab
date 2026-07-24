#!/usr/bin/env bash
set -Eeuo pipefail

readonly appdata_root="/srv/appdata/docker"
readonly paperless_root="$appdata_root/paperless"

actual_source="$(findmnt -n -o SOURCE --target "$appdata_root")"
[[ "$actual_source" == "rpool/appdata/docker" ]] || {
  echo "$appdata_root is mounted from $actual_source, expected rpool/appdata/docker" >&2
  exit 1
}

install -d -m 0750 "$paperless_root"
install -d -o 1000 -g 1000 -m 0750 \
  "$paperless_root/data" \
  "$paperless_root/media" \
  "$paperless_root/media/trash" \
  "$paperless_root/export" \
  "$paperless_root/consume"
install -d -o 999 -g 999 -m 0700 \
  "$paperless_root/postgres" \
  "$paperless_root/valkey"
install -d -o 10001 -g 10001 -m 0700 \
  "$paperless_root/gpt" \
  "$paperless_root/gpt/prompts" \
  "$paperless_root/gpt/config" \
  "$paperless_root/gpt/db"
install -d -m 0700 \
  "$paperless_root/backups" \
  "$paperless_root/restore-tests"
