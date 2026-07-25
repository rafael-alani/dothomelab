#!/usr/bin/env bash
set -Eeuo pipefail

readonly apps_ctid="${STORYTELLER_APPS_CTID:-112}"
readonly backup_script="/opt/dothomelab/hosts/apps/storyteller/backup-database.sh"

[[ "$apps_ctid" =~ ^[0-9]+$ ]] || {
  printf 'Invalid STORYTELLER_APPS_CTID: %s\n' "$apps_ctid" >&2
  exit 2
}
pct status "$apps_ctid" | grep -q "status: running" || {
  printf 'Apps LXC %s is not running\n' "$apps_ctid" >&2
  exit 1
}
pct exec "$apps_ctid" -- test -x "$backup_script" || {
  printf 'Storyteller database-backup script is missing in Apps\n' >&2
  exit 1
}

pct exec "$apps_ctid" -- "$backup_script"
