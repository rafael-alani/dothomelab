#!/usr/bin/env bash
set -Eeuo pipefail

readonly apps_ctid="${GRIMMORY_APPS_CTID:-112}"
readonly backup_script="/opt/dothomelab/hosts/apps/grimmory/backup-database.sh"

[[ "$apps_ctid" =~ ^[0-9]+$ ]] || {
  echo "Invalid GRIMMORY_APPS_CTID: $apps_ctid" >&2
  exit 2
}
pct status "$apps_ctid" | grep -q "status: running" || {
  echo "Apps LXC $apps_ctid is not running" >&2
  exit 1
}
pct exec "$apps_ctid" -- test -x "$backup_script" || {
  echo "Grimmory logical-backup script is missing in Apps" >&2
  exit 1
}

pct exec "$apps_ctid" -- "$backup_script"
