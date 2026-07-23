#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

readonly CONFIG_FILE="${DOTHOMELAB_BACKUP_CONFIG:-/etc/dothomelab/pbs-appdata.conf}"
readonly LOCK_FILE="/run/lock/dothomelab-appdata-backup.lock"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*"
  exit 1
}

run_hooks() {
  local hook_dir="$1"
  local hook

  [[ -d "$hook_dir" ]] || return 0
  shopt -s nullglob
  for hook in "$hook_dir"/*; do
    [[ -x "$hook" && -f "$hook" ]] || continue
    log "Running hook: $hook"
    "$hook"
  done
  shopt -u nullglob
}

[[ $EUID -eq 0 ]] || die "This backup must run as root."
[[ -r "$CONFIG_FILE" ]] || die "Missing configuration: $CONFIG_FILE"

# The live file is root-owned and is never committed to Git.
# shellcheck disable=SC1090
source "$CONFIG_FILE"

: "${APPDATA_DATASET:=rpool/appdata/docker}"
: "${APPDATA_MOUNT:=/srv/appdata/docker}"
: "${PBS_BACKUP_ID:=afa-appdata}"
: "${PBS_PASSWORD_FILE:=/etc/dothomelab/pbs-appdata.token}"
: "${PBS_KEY_FILE:=/etc/dothomelab/pbs-appdata.key}"
: "${RECOVERY_ENV_FILE:=/root/.env}"
: "${PRE_HOOK_DIR:=/etc/dothomelab/backup-pre.d}"
: "${POST_HOOK_DIR:=/etc/dothomelab/backup-post.d}"
: "${QUIESCE_CTIDS:=}"

: "${PBS_REPOSITORY:?PBS_REPOSITORY is required in $CONFIG_FILE}"
: "${PBS_FINGERPRINT:?PBS_FINGERPRINT is required in $CONFIG_FILE}"

export PBS_REPOSITORY PBS_FINGERPRINT PBS_PASSWORD_FILE

for command_name in flock lxc-freeze lxc-unfreeze pct proxmox-backup-client sync zfs; do
  command -v "$command_name" >/dev/null || die "Required command not found: $command_name"
done

[[ -s "$PBS_PASSWORD_FILE" ]] || die "Missing PBS API token file: $PBS_PASSWORD_FILE"
[[ -s "$PBS_KEY_FILE" ]] || die "Missing PBS encryption key: $PBS_KEY_FILE"
[[ -d "$APPDATA_MOUNT" ]] || die "Appdata mount is missing: $APPDATA_MOUNT"

actual_mount="$(zfs get -H -o value mountpoint "$APPDATA_DATASET")"
[[ "$actual_mount" == "$APPDATA_MOUNT" ]] ||
  die "$APPDATA_DATASET is mounted at $actual_mount, expected $APPDATA_MOUNT"

exec 9>"$LOCK_FILE"
flock -n 9 || die "Another appdata backup is already running."

snapshot_suffix="pbs-$(date --utc +%Y%m%dT%H%M%SZ)"
snapshot_name="${APPDATA_DATASET}@${snapshot_suffix}"
snapshot_path="${APPDATA_MOUNT}/.zfs/snapshot/${snapshot_suffix}"
snapshot_created=0
post_hooks_pending=0
declare -a frozen_ctids=()

unfreeze_guests() {
  local ctid
  local failed=0
  local -a still_frozen=()

  for ctid in "${frozen_ctids[@]}"; do
    log "Unfreezing LXC $ctid"
    if ! lxc-unfreeze -n "$ctid"; then
      still_frozen+=("$ctid")
      failed=1
    fi
  done
  frozen_ctids=("${still_frozen[@]}")
  return "$failed"
}

cleanup() {
  local exit_code=$?

  trap - EXIT INT TERM
  if ! unfreeze_guests; then
    log "ERROR: one or more LXCs could not be unfrozen"
    exit_code=1
  fi
  if ((post_hooks_pending)); then
    if ! run_hooks "$POST_HOOK_DIR"; then
      log "ERROR: one or more post-backup hooks failed"
      exit_code=1
    fi
    post_hooks_pending=0
  fi
  if ((snapshot_created)) && zfs list -H -t snapshot "$snapshot_name" >/dev/null 2>&1; then
    log "Destroying temporary snapshot $snapshot_name"
    if ! zfs destroy "$snapshot_name"; then
      log "ERROR: temporary snapshot could not be destroyed"
      exit_code=1
    fi
  fi
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

log "Starting appdata backup"
run_hooks "$PRE_HOOK_DIR"
post_hooks_pending=1

sync
for ctid in $QUIESCE_CTIDS; do
  [[ "$ctid" =~ ^[0-9]+$ ]] || die "Invalid LXC ID in QUIESCE_CTIDS: $ctid"
  if pct status "$ctid" 2>/dev/null | grep -q 'status: running'; then
    log "Freezing LXC $ctid for a consistent snapshot"
    lxc-freeze -n "$ctid"
    frozen_ctids+=("$ctid")
  fi
done

sync
log "Creating temporary snapshot $snapshot_name"
zfs snapshot "$snapshot_name"
snapshot_created=1
[[ -d "$snapshot_path" ]] || die "Snapshot path is unavailable: $snapshot_path"

unfreeze_guests
run_hooks "$POST_HOOK_DIR"
post_hooks_pending=0

backup_specs=("appdata.pxar:${snapshot_path}")
if [[ -s "$RECOVERY_ENV_FILE" ]]; then
  backup_specs+=("recovery-env.conf:${RECOVERY_ENV_FILE}")
else
  log "WARNING: $RECOVERY_ENV_FILE is absent or empty; this run contains appdata only"
fi

log "Uploading encrypted backup as host/$PBS_BACKUP_ID"
proxmox-backup-client backup "${backup_specs[@]}" \
  --backup-id "$PBS_BACKUP_ID" \
  --backup-type host \
  --change-detection-mode data \
  --crypt-mode encrypt \
  --keyfile "$PBS_KEY_FILE" \
  --repository "$PBS_REPOSITORY"

log "Appdata backup completed successfully"
