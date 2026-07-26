#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly repo_root="$(cd -- "$script_dir/../.." && pwd)"
inventory_file="${DOTHOMELAB_INVENTORY:-$repo_root/provision/inventory.env}"
if [[ ! -r "$inventory_file" && -r /etc/dothomelab/inventory.env ]]; then
  inventory_file="/etc/dothomelab/inventory.env"
fi
# shellcheck disable=SC1091
source "$inventory_file"

readonly addon_slug="b9845f46_govee2mqtt"
readonly addon_container="addon_b9845f46_govee2mqtt"
readonly addon_options="/mnt/data/supervisor/addons/data/$addon_slug/options.json"
readonly rollback_dir="/mnt/data/supervisor/homeassistant/upgrade-rollbacks/dothomelab-govee"
readonly recovery_env_file="${DOTHOMELAB_ENV_FILE:-/root/.env}"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

guest_exec() {
  qm guest exec "$HAOS_VMID" --timeout 300 -- "$@" |
    python3 -c '
import json
import sys

result = json.load(sys.stdin)
sys.stdout.write(result.get("out-data", ""))
sys.stderr.write(result.get("err-data", ""))
raise SystemExit(result.get("exitcode", 1))
'
}

guest_exec_stdin() {
  qm guest exec "$HAOS_VMID" --timeout 300 --pass-stdin 1 -- "$@" |
    python3 -c '
import json
import sys

result = json.load(sys.stdin)
sys.stdout.write(result.get("out-data", ""))
sys.stderr.write(result.get("err-data", ""))
raise SystemExit(result.get("exitcode", 1))
'
}

wait_for_addon() {
  local deadline=$((SECONDS + 180))
  local state
  until state="$(
    guest_exec ha apps info "$addon_slug" --raw-json |
      python3 -c '
import json
import sys

print(json.load(sys.stdin).get("data", {}).get("state", ""))
'
  )" && [[ "$state" == "started" ]] &&
    curl -fsS --max-time 10 "http://$HAOS_IP:8056/api/devices" |
      python3 -c '
import json
import sys

devices = json.load(sys.stdin)
physical = sorted(
    device.get("sku")
    for device in devices
    if device.get("sku") in {"H60A1", "H6072"}
)
raise SystemExit(physical != ["H6072", "H60A1", "H60A1"])
'; do
    ((SECONDS < deadline)) || return 1
    sleep 3
  done
}

wait_for_platform_metadata() {
  local since="$1"
  local deadline=$((SECONDS + 180))
  local count
  until count="$(
    guest_exec sh -c \
      "docker logs --since '$since' '$addon_container' 2>&1 |
        grep -c 'Platform API: devices.types.light' || true"
  )" && [[ "$count" =~ ^[0-9]+$ ]] && ((count >= 3)); do
    ((SECONDS < deadline)) || return 1
    sleep 3
  done
}

restore_options() {
  local rollback="$1"
  local restore_script='
set -eu
options="$(cat)"
payload="$(printf "%s" "$options" | jq -c "{options: .}")"
curl -fsS \
  -X POST \
  -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  --data "$payload" \
  http://supervisor/addons/b9845f46_govee2mqtt/options |
  jq -e ".result == \"ok\"" >/dev/null
'
  guest_exec sh -c \
    'cat "$1" | docker exec -i hassio_cli sh -c "$2"' \
    sh "$rollback" "$restore_script" >/dev/null
}

[[ $EUID -eq 0 ]] || die "Run this configuration as root on Proxmox."
for command_name in curl python3 qm; do
  command -v "$command_name" >/dev/null ||
    die "Required command is missing: $command_name"
done

if [[ -z "${GOVEE_API_KEY:-}" ]]; then
  [[ -r "$recovery_env_file" ]] ||
    die "GOVEE_API_KEY is unset and $recovery_env_file is not readable"
  # shellcheck disable=SC1091
  source "$repo_root/hosts/common/load-env.sh"
  load_dothomelab_env "$recovery_env_file"
fi
[[ "${GOVEE_API_KEY:-}" =~ ^[A-Za-z0-9_-]{16,128}$ ]] ||
  die "GOVEE_API_KEY is missing or malformed"

qm status "$HAOS_VMID" | grep -q 'status: running' ||
  die "HAOS VM $HAOS_VMID is not running"
qm agent "$HAOS_VMID" ping >/dev/null ||
  die "HAOS VM $HAOS_VMID guest agent is unavailable"

check_script='
set -eu
IFS= read -r govee_key
info="$(
  curl -fsS \
    -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
    http://supervisor/addons/b9845f46_govee2mqtt/info
)"
if printf "%s" "$info" |
  jq -e \
    --arg key "$govee_key" \
    ".data.state == \"started\" and
     .data.options.temperature_scale == \"C\" and
     .data.options.govee_api_key == \$key and
     (.data.options | has(\"govee_email\") | not) and
     (.data.options | has(\"govee_password\") | not)" >/dev/null; then
  printf "current\n"
else
  printf "change-required\n"
fi
'

apply_script='
set -eu
IFS= read -r govee_key
info="$(
  curl -fsS \
    -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
    http://supervisor/addons/b9845f46_govee2mqtt/info
)"
options="$(
  printf "%s" "$info" |
    jq -c \
      --arg key "$govee_key" \
      ".data.options |
       del(.govee_email, .govee_password) |
       .temperature_scale = \"C\" |
       .govee_api_key = \$key"
)"
payload="$(printf "%s" "$options" | jq -c "{options: .}")"
curl -fsS \
  -X POST \
  -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  --data "$payload" \
  http://supervisor/addons/b9845f46_govee2mqtt/options |
  jq -e ".result == \"ok\"" >/dev/null
'

configuration_state="$(
  printf '%s\n' "$GOVEE_API_KEY" |
    guest_exec_stdin docker exec -i hassio_cli sh -c "$check_script"
)" || die "Failed to inspect Govee2MQTT options"

case "$configuration_state" in
  current)
    wait_for_addon ||
      die "Govee2MQTT options match, but its physical inventory is unhealthy"
    log "Govee2MQTT already has the recovery-managed Platform API configuration."
    ;;
  change-required)
    stamp="$(date --utc +%Y%m%dT%H%M%SZ)"
    rollback="$rollback_dir/options.$stamp.json"
    guest_exec mkdir -p "$rollback_dir" >/dev/null
    guest_exec chmod 0700 "$rollback_dir" >/dev/null
    guest_exec cp -p "$addon_options" "$rollback" >/dev/null
    guest_exec chmod 0600 "$rollback" >/dev/null
    started_at="$(date --utc +%Y-%m-%dT%H:%M:%SZ)"
    if ! printf '%s\n' "$GOVEE_API_KEY" |
      guest_exec_stdin docker exec -i hassio_cli sh -c "$apply_script" >/dev/null; then
      if restore_options "$rollback"; then
        die "Failed to reconcile Govee2MQTT options; restored $rollback"
      fi
      die "Failed to reconcile Govee2MQTT options; automatic restore failed and rollback remains at $rollback"
    fi
    if ! guest_exec ha apps restart "$addon_slug" >/dev/null ||
      ! wait_for_addon ||
      ! wait_for_platform_metadata "$started_at"; then
      if restore_options "$rollback"; then
        guest_exec ha apps restart "$addon_slug" >/dev/null || true
        wait_for_addon || true
        die "Govee2MQTT failed Platform API validation; restored $rollback"
      fi
      die "Govee2MQTT failed Platform API validation; automatic restore failed and rollback remains at $rollback"
    fi
    log "Govee2MQTT Platform API configuration accepted; rollback retained at $rollback"
    ;;
  *)
    die "Unexpected Govee2MQTT configuration state"
    ;;
esac
