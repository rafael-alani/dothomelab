#!/usr/bin/env bash
set -Eeuo pipefail

readonly ctid=110
readonly interval_seconds=$((14 * 24 * 60 * 60))
readonly env_file=/root/.env
readonly state_root=/srv/appdata/docker/proton-drive
readonly current_cycle_file="$state_root/current-cycle"
readonly last_cycle_epoch_file="$state_root/last-cycle.epoch"
readonly runtime_root=/run/dothomelab-proton-backup
readonly guest_runner=/usr/local/sbin/dothomelab-proton-backup-runner
readonly lock_file=/run/lock/dothomelab-proton-backup.lock

force=false
case "${1:-}" in
  "")
    ;;
  --force)
    force=true
    ;;
  *)
    echo "Usage: $0 [--force]" >&2
    exit 2
    ;;
esac

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

validate_cycle() {
  [[ "$1" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] ||
    die "Invalid saved Proton backup cycle ID"
}

[[ $EUID -eq 0 ]] || die "Run the Proton backup as root on the PVE host"
for command_name in findmnt flock pct; do
  command -v "$command_name" >/dev/null ||
    die "Required command is missing: $command_name"
done
[[ -s "$env_file" && -f "$env_file" && ! -L "$env_file" ]] ||
  die "$env_file must be a non-empty regular file, not a symlink"
[[ "$(stat -c %a "$env_file")" == "600" ]] ||
  die "$env_file must have mode 0600"
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker)" == "rpool/appdata/docker" ]] ||
  die "/srv/appdata/docker is not backed by rpool/appdata/docker"
[[ "$(findmnt -n -o SOURCE -T /vault/shared/media/obsidian)" == "vault/shared" ]] ||
  die "/vault/shared/media/obsidian is not backed by vault/shared"
[[ "$(findmnt -n -o SOURCE -T /vault/shared/media/photos)" == "vault/shared" ]] ||
  die "/vault/shared/media/photos is not backed by vault/shared"
[[ "$(pct status "$ctid")" == "status: running" ]] ||
  die "Infra LXC $ctid is not running"

exec 9>"$lock_file"
if ! flock --nonblock 9; then
  die "Another Proton backup is already running on the PVE host"
fi

now_epoch="$(date +%s)"
[[ "$now_epoch" =~ ^[0-9]+$ ]] || die "Could not read the current epoch"

if [[ -s "$current_cycle_file" ]]; then
  cycle_id="$(tr -d '\n' <"$current_cycle_file")"
  validate_cycle "$cycle_id"
  log "Retrying incomplete Proton backup cycle $cycle_id"
else
  if [[ "$force" == false && -s "$last_cycle_epoch_file" ]]; then
    last_epoch="$(tr -d '\n' <"$last_cycle_epoch_file")"
    [[ "$last_epoch" =~ ^[0-9]+$ ]] ||
      die "$last_cycle_epoch_file is invalid"
    ((last_epoch <= now_epoch)) ||
      die "The saved Proton backup time is in the future"
    next_epoch=$((last_epoch + interval_seconds))
    if ((now_epoch < next_epoch)); then
      log "Fortnightly Proton backup is not due until $(date --date="@$next_epoch" --iso-8601=seconds)"
      exit 0
    fi
  fi
  cycle_id="$(date --utc +%Y%m%dT%H%M%SZ)"
  validate_cycle "$cycle_id"
  log "Starting new Proton backup cycle $cycle_id"
fi

runtime_prepared=false
cleanup_runtime() {
  if [[ "$runtime_prepared" == true ]]; then
    pct exec "$ctid" -- rm -rf -- "$runtime_root" >/dev/null 2>&1 ||
      log "WARNING: could not remove the temporary Infra environment staging directory"
  fi
}
trap cleanup_runtime EXIT

pct exec "$ctid" -- install -d -o 1000 -g 1000 -m 0700 \
  "$runtime_root" "$runtime_root/input" "$runtime_root/work"
runtime_prepared=true
pct push "$ctid" "$env_file" "$runtime_root/input/root.env" --perms 0600
pct exec "$ctid" -- chown 1000:1000 "$runtime_root/input/root.env"
pct exec "$ctid" -- test -x "$guest_runner" ||
  die "The Infra Proton backup runner is not installed"

pct exec "$ctid" -- "$guest_runner" "$cycle_id"

[[ ! -e "$current_cycle_file" ]] ||
  die "Infra returned success but cycle $cycle_id is still marked incomplete"
for dataset in obsidian photos environment; do
  dataset_cycle="$state_root/sources/$dataset/last-success.cycle"
  [[ -s "$dataset_cycle" && "$(<"$dataset_cycle")" == "$cycle_id" ]] ||
    die "Infra returned success without recording $dataset for cycle $cycle_id"
done
[[ -s "$last_cycle_epoch_file" ]] ||
  die "Infra returned success without recording a complete-cycle time"

log "Fortnightly Proton backup cycle $cycle_id completed and verified"
