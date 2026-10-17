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

# pct exec output is not reliably retained by the host journal. Keep a private
# per-cycle log in canonical appdata so a failed on-demand container is diagnosable.
umask 077
log_root=/srv/appdata/docker/proton-drive/run-logs
install -d -m 0700 "$log_root"
exec >>"$log_root/$cycle_id.log" 2>&1
printf '%s Starting Infra attempt for cycle %s\n' "$(date --iso-8601=seconds)" "$cycle_id"

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

docker compose --env-file "$environment_file" -f "$compose_file" --profile proton config --quiet

proton_backup begin-cycle "$cycle_id"

# Syncthing is the server's only intended writer for the Obsidian vault.
# Pausing it only while the local archive is produced gives that source a
# point-in-time image without granting the Proton container write access.
docker pause "$syncthing_container" >/dev/null
paused=true
proton_backup stage obsidian "$cycle_id"
docker unpause "$syncthing_container" >/dev/null
paused=false

proton_backup upload obsidian "$cycle_id"

# Finish small independent sources before the large external-photo archive.
# Each upload is verified and extraction-tested before its old generations
# are eligible for retention; a failed source keeps the whole cycle pending.
for dataset in environment immich photos; do
  proton_backup stage "$dataset" "$cycle_id"
  proton_backup upload "$dataset" "$cycle_id"
done
proton_backup complete-cycle "$cycle_id"
