#!/usr/bin/env bash
set -Eeuo pipefail

readonly servarr_ctid="${LISTENARR_SERVARR_CTID:-102}"
readonly backup_script="/opt/dothomelab/hosts/servarr/listenarr/backup-database.sh"

[[ "$servarr_ctid" =~ ^[0-9]+$ ]] || {
  echo "Invalid LISTENARR_SERVARR_CTID: $servarr_ctid" >&2
  exit 2
}
pct status "$servarr_ctid" | grep -q "status: running" || {
  echo "Servarr LXC $servarr_ctid is not running" >&2
  exit 1
}
pct exec "$servarr_ctid" -- test -x "$backup_script" || {
  echo "Listenarr database-backup script is missing in Servarr" >&2
  exit 1
}

pct exec "$servarr_ctid" -- "$backup_script"
