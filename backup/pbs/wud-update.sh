#!/usr/bin/env bash
set -Eeuo pipefail

readonly LOCK_FILE="/run/lock/dothomelab-wud-update.lock"
readonly INFRA_CTID="${WUD_INFRA_CTID:-110}"
readonly RUNNER="/usr/local/sbin/dothomelab-wud-runner"
readonly DRY_RUN="${WUD_UPDATE_DRY_RUN:-false}"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

[[ $EUID -eq 0 ]] || {
  log "ERROR: run as root"
  exit 1
}
[[ "$INFRA_CTID" =~ ^[0-9]+$ ]] || {
  log "ERROR: invalid WUD_INFRA_CTID: $INFRA_CTID"
  exit 1
}
[[ "$DRY_RUN" == "true" || "$DRY_RUN" == "false" ]] || {
  log "ERROR: WUD_UPDATE_DRY_RUN must be true or false"
  exit 1
}

for command_name in flock pct; do
  command -v "$command_name" >/dev/null || {
    log "ERROR: required command not found: $command_name"
    exit 1
  }
done

exec 9>"$LOCK_FILE"
flock -n 9 || {
  log "ERROR: another WUD update run is already active"
  exit 1
}

pct status "$INFRA_CTID" | grep -q "status: running" || {
  log "ERROR: infra LXC $INFRA_CTID is not running"
  exit 1
}
pct exec "$INFRA_CTID" -- test -x "$RUNNER" || {
  log "ERROR: WUD runner is missing in infra LXC $INFRA_CTID"
  exit 1
}

runner_args=()
if [[ "$DRY_RUN" == "true" ]]; then
  runner_args+=(--dry-run)
fi

log "Starting backup-gated WUD update run"
pct exec "$INFRA_CTID" -- "$RUNNER" "${runner_args[@]}"
log "Backup-gated WUD update run completed"
