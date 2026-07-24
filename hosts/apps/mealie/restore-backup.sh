#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <Mealie backup ZIP>" >&2
  exit 2
fi

archive="$1"
base_url="${MEALIE_RESTORE_URL:-http://127.0.0.1:19925}"
bootstrap_user="${MEALIE_BOOTSTRAP_USER:-changeme@email.com}"
bootstrap_password="${MEALIE_BOOTSTRAP_PASSWORD:-MyPassword}"

[[ -s "$archive" ]] || {
  echo "Backup archive is missing or empty: $archive" >&2
  exit 1
}

token="$(
  curl --fail --silent --show-error \
    --data-urlencode "username=$bootstrap_user" \
    --data-urlencode "password=$bootstrap_password" \
    --data-urlencode "remember_me=false" \
    "$base_url/api/auth/token" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

curl --fail --silent --show-error \
  --header "Authorization: Bearer $token" \
  --form "archive=@$archive;type=application/zip" \
  "$base_url/api/admin/backups/upload" >/dev/null

file_name="$(basename "$archive")"
encoded_name="$(
  python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' \
    "$file_name"
)"

curl --fail --silent --show-error \
  --request POST \
  --header "Authorization: Bearer $token" \
  "$base_url/api/admin/backups/$encoded_name/restore" >/dev/null

printf 'Mealie accepted and restored %s through its backup API.\n' "$file_name"
