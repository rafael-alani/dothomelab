#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

readonly CONFIG_FILE="${DOTHOMELAB_BACKUP_CONFIG:-/etc/dothomelab/pbs-appdata.conf}"

usage() {
  echo "Usage: $0 <host/backup-id/timestamp> <empty-target-path>"
}

[[ $EUID -eq 0 ]] || {
  echo "This restore must run as root." >&2
  exit 1
}
[[ $# -eq 2 ]] || {
  usage >&2
  exit 2
}
[[ -r "$CONFIG_FILE" ]] || {
  echo "Missing configuration: $CONFIG_FILE" >&2
  exit 1
}

# shellcheck disable=SC1090
source "$CONFIG_FILE"

: "${PBS_PASSWORD_FILE:=/etc/dothomelab/pbs-appdata.token}"
: "${PBS_KEY_FILE:=/etc/dothomelab/pbs-appdata.key}"
: "${PBS_REPOSITORY:?PBS_REPOSITORY is required in $CONFIG_FILE}"
: "${PBS_FINGERPRINT:?PBS_FINGERPRINT is required in $CONFIG_FILE}"

export PBS_REPOSITORY PBS_FINGERPRINT PBS_PASSWORD_FILE

snapshot="$1"
target="$2"

case "$target" in
  / | /srv | /srv/appdata | /srv/appdata/docker | /vault | /vault/shared)
    echo "Refusing unsafe restore target: $target" >&2
    exit 1
    ;;
esac

[[ ! -e "$target" ]] || {
  echo "Restore target already exists: $target" >&2
  exit 1
}
mkdir -p "$(dirname "$target")"

proxmox-backup-client restore "$snapshot" appdata.pxar "$target" \
  --keyfile "$PBS_KEY_FILE" \
  --repository "$PBS_REPOSITORY"

file_count="$(find "$target" -xdev -type f | wc -l)"
size="$(du -sh "$target" | awk '{print $1}')"
echo "Restored $file_count files ($size) to $target"
