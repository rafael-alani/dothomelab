#!/usr/bin/env bash
set -euo pipefail

compose_file=/opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml
lock_file=/run/lock/dothomelab-obsidian-proton-backup.lock
syncthing_container=syncthing
paused=false

exec 9>"$lock_file"
if ! flock --nonblock 9; then
  echo "Another Obsidian Proton backup is already running" >&2
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

if [[ "$(docker inspect --format '{{.State.Running}}' "$syncthing_container" 2>/dev/null)" != true ]]; then
  echo "Syncthing is not running" >&2
  exit 1
fi

# Syncthing is the server's only writer for the vault. Pausing it makes the
# archive point-in-time without giving the Proton container write access.
docker pause "$syncthing_container" >/dev/null
paused=true
docker compose -f "$compose_file" --profile proton run --rm proton-drive backup stage
docker unpause "$syncthing_container" >/dev/null
paused=false

docker compose -f "$compose_file" --profile proton run --rm proton-drive backup upload
