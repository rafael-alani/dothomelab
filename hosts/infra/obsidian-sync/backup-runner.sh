#!/usr/bin/env bash
set -Eeuo pipefail

compose_file=/opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml
lock_file=/run/lock/dothomelab-proton-backup.lock
runtime_root=/run/dothomelab-proton-backup
environment_file="$runtime_root/input/root.env"
volatile_work="$runtime_root/work"
syncthing_container=syncthing
paused=false

if [[ $# -ne 1 ]] || [[ ! "$1" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
  echo "Usage: $0 <YYYYMMDDTHHMMSSZ-cycle-id>" >&2
  exit 2
fi
cycle_id="$1"

exec 9>"$lock_file"
if ! flock --nonblock 9; then
  echo "Another Proton backup is already running in Infra" >&2
  exit 1
fi

resume_syncthing() {
  if [[ "$paused" == true ]]; then
    docker unpause "$syncthing_container" >/dev/null 2>&1 || true
  fi
}
trap resume_syncthing EXIT

if [[ ! -r "$compose_file" ]]; then
  echo "Missing deployed Compose definition: $compose_file" >&2
  exit 1
fi
if [[ ! -f "$environment_file" || -L "$environment_file" ]]; then
  echo "Missing safe host environment staging file: $environment_file" >&2
  exit 1
fi
if [[ "$(stat -c %a "$environment_file")" != 600 ]]; then
  echo "$environment_file must have mode 0600" >&2
  exit 1
fi
if [[ ! -d "$volatile_work" ]]; then
  echo "Missing volatile environment backup work directory: $volatile_work" >&2
  exit 1
fi
if [[ "$(docker inspect --format '{{.State.Running}}' "$syncthing_container" 2>/dev/null)" != true ]]; then
  echo "Syncthing is not running" >&2
  exit 1
fi

proton_backup() {
  docker compose \
    --env-file "$environment_file" \
    -f "$compose_file" \
    --profile proton \
    run \
    --rm \
    --volume "$runtime_root/input:/sources/environment:ro" \
    --volume "$volatile_work:/volatile-work" \
    proton-drive \
    backup \
    "$@"
}

proton_backup begin-cycle "$cycle_id"

# Syncthing is the server's only intended writer for the Obsidian vault.
# Pausing it only while the local archive is produced gives that source a
# point-in-time image without granting the Proton container write access.
docker pause "$syncthing_container" >/dev/null
paused=true
proton_backup stage obsidian "$cycle_id"
docker unpause "$syncthing_container" >/dev/null
paused=false

# Photos are read-only in Apps and are not modified by this runner. GNU tar
# fails the stage if it detects a concurrent external write, so a failed cycle
# is retained and retried by the host timer instead of uploading a torn copy.
proton_backup stage photos "$cycle_id"
proton_backup stage environment "$cycle_id"

proton_backup upload obsidian "$cycle_id"
proton_backup upload photos "$cycle_id"
proton_backup upload environment "$cycle_id"
proton_backup complete-cycle "$cycle_id"
