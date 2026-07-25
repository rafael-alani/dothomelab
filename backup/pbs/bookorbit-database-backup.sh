#!/usr/bin/env bash
set -Eeuo pipefail

readonly apps_ctid="${BOOKORBIT_APPS_CTID:-112}"
readonly backup_script="/opt/dothomelab/hosts/apps/bookorbit/backup-database.sh"

[[ "$apps_ctid" =~ ^[0-9]+$ ]] || {
  echo "Invalid BOOKORBIT_APPS_CTID: $apps_ctid" >&2
  exit 2
}
pct status "$apps_ctid" | grep -q "status: running" || {
  echo "Apps LXC $apps_ctid is not running" >&2
  exit 1
}
pct exec "$apps_ctid" -- test -x "$backup_script" || {
  echo "BookOrbit logical-backup script is missing in Apps" >&2
  exit 1
}

pct exec "$apps_ctid" -- "$backup_script"
