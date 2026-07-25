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

readonly config="/mnt/data/supervisor/homeassistant/configuration.yaml"
readonly rollback_dir="/mnt/data/supervisor/homeassistant/upgrade-rollbacks/dothomelab-proxy"
readonly desired_proxy="${CT_IP[110]}"
readonly legacy_proxy="192.168.1.110"

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

wait_for_core() {
  local deadline=$((SECONDS + 300))
  until [[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
    --max-time 5 "http://$HAOS_IP:8123/" || true)" == "200" ]]; do
    ((SECONDS < deadline)) || return 1
    sleep 5
  done
}

[[ $EUID -eq 0 ]] || die "Run this configuration as root on Proxmox."
for command_name in curl python3 qm; do
  command -v "$command_name" >/dev/null ||
    die "Required command is missing: $command_name"
done
[[ "$desired_proxy" =~ ^192\.168\.0\.[0-9]{1,3}$ ]] ||
  die "Unexpected Infra proxy address: $desired_proxy"
qm status "$HAOS_VMID" | grep -q 'status: running' ||
  die "HAOS VM $HAOS_VMID is not running"
qm agent "$HAOS_VMID" ping >/dev/null ||
  die "HAOS VM $HAOS_VMID guest agent is unavailable"
guest_exec test -s "$config" >/dev/null ||
  die "Home Assistant configuration is missing: $config"

desired_count="$(
  guest_exec sh -c \
    "grep -Ec '^[[:space:]]*-[[:space:]]*${desired_proxy//./\\.}[[:space:]]*$' '$config' || true"
)"
legacy_count="$(
  guest_exec sh -c \
    "grep -Ec '^[[:space:]]*-[[:space:]]*${legacy_proxy//./\\.}[[:space:]]*$' '$config' || true"
)"

if [[ "$desired_count" == "1" && "$legacy_count" == "0" ]]; then
  log "Home Assistant already trusts Nginx Proxy Manager at $desired_proxy."
  exit 0
fi
[[ "$desired_count" == "0" && "$legacy_count" == "1" ]] ||
  die "Refusing to guess Home Assistant trusted_proxies structure (desired=$desired_count legacy=$legacy_count)"

stamp="$(date --utc +%Y%m%dT%H%M%SZ)"
rollback="$rollback_dir/configuration.yaml.$stamp"
guest_exec mkdir -p "$rollback_dir" >/dev/null
guest_exec chmod 0700 "$rollback_dir" >/dev/null
guest_exec cp -p "$config" "$rollback" >/dev/null
guest_exec sed -i "s/${legacy_proxy//./\\.}/${desired_proxy}/" "$config" >/dev/null

if ! guest_exec ha core check --no-progress >/dev/null; then
  guest_exec cp -p "$rollback" "$config" >/dev/null
  die "Home Assistant configuration validation failed; restored $rollback"
fi

if ! guest_exec ha core restart >/dev/null || ! wait_for_core; then
  guest_exec cp -p "$rollback" "$config" >/dev/null
  guest_exec ha core restart >/dev/null || true
  wait_for_core || true
  die "Home Assistant did not return healthy after the proxy change; restored $rollback"
fi

log "Home Assistant now trusts Nginx Proxy Manager at $desired_proxy; rollback retained at $rollback"
