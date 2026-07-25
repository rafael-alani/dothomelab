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

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

[[ $EUID -eq 0 ]] || die "Run this restore as root on Proxmox."
for command_name in python3 qm qmrestore sha256sum vma zstd zstdcat; do
  command -v "$command_name" >/dev/null ||
    die "Required command is missing: $command_name"
done

if qm status "$HAOS_VMID" >/dev/null 2>&1; then
  log "HAOS VM $HAOS_VMID already exists; retaining it without disk replacement."
  exit 0
fi

[[ -d "$HAOS_VM_BACKUP_DIR" ]] ||
  die "Missing HAOS recovery directory: $HAOS_VM_BACKUP_DIR"
mapfile -t archives < <(
  find "$HAOS_VM_BACKUP_DIR" -maxdepth 1 -type f \
    -name "vzdump-qemu-${HAOS_VMID}-*.vma.zst" -printf '%T@ %p\n' |
    sort -nr |
    cut -d' ' -f2-
)
((${#archives[@]} > 0)) ||
  die "No VM $HAOS_VMID recovery image exists in $HAOS_VM_BACKUP_DIR"
archive="${archives[0]}"
checksum="$archive.sha256"
[[ -s "$checksum" ]] || die "Missing checksum sidecar: $checksum"

log "Verifying recovery image before creating VM $HAOS_VMID"
(
  cd -- "$HAOS_VM_BACKUP_DIR"
  sha256sum --check "$(basename -- "$checksum")"
)
zstd -t "$archive"
zstdcat "$archive" | vma verify -

log "Restoring VM $HAOS_VMID from $(basename -- "$archive")"
if ! qmrestore "$archive" "$HAOS_VMID" \
  --storage "$HAOS_VM_STORAGE" \
  --unique 0; then
  die "qmrestore failed; inspect the partial VM manually before retrying"
fi

qm set "$HAOS_VMID" \
  --agent 1 \
  --bios "$HAOS_BIOS" \
  --cores "$HAOS_CORES" \
  --cpu "$HAOS_CPU_TYPE" \
  --memory "$HAOS_MEMORY" \
  --name "$HAOS_VM_NAME" \
  --net0 "virtio=$HAOS_MAC,bridge=$PVE_BRIDGE" \
  --onboot 1 \
  --scsihw "$HAOS_SCSIHW" \
  --startup "$HAOS_STARTUP" \
  --protection 1
qm start "$HAOS_VMID"

deadline=$((SECONDS + 600))
until qm agent "$HAOS_VMID" ping >/dev/null 2>&1; do
  ((SECONDS < deadline)) ||
    die "VM $HAOS_VMID restored but its guest agent did not become ready"
  sleep 5
done

qm guest exec "$HAOS_VMID" -- ha info --raw-json |
  python3 -c '
import json
import sys
outer = json.load(sys.stdin)
inner = json.loads(outer["out-data"])
data = inner["data"]
if data.get("state") != "running" or not data.get("supported"):
    raise SystemExit("restored Home Assistant is not running and supported")
'

log "HAOS VM $HAOS_VMID restored and running; native HA backups remain in $HAOS_NATIVE_BACKUP_DIR"
