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

check_only=false
case "${1:-}" in
  "")
    ;;
  --check)
    check_only=true
    ;;
  -h | --help)
    printf 'Usage: %s [--check]\n' "$0"
    exit 0
    ;;
  *)
    printf 'Unknown option: %s\n' "$1" >&2
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

[[ $EUID -eq 0 ]] || die "Run this backup as root on Proxmox."
for command_name in python3 qm sha256sum vma vzdump zstd zstdcat; do
  command -v "$command_name" >/dev/null ||
    die "Required command is missing: $command_name"
done

qm status "$HAOS_VMID" | grep -q 'status: running' ||
  die "HAOS VM $HAOS_VMID is not running"
qm agent "$HAOS_VMID" ping >/dev/null ||
  die "HAOS VM $HAOS_VMID guest agent is unavailable"

ha_info="$(
  qm guest exec "$HAOS_VMID" -- ha info --raw-json |
    python3 -c '
import json
import sys
outer = json.load(sys.stdin)
inner = json.loads(outer["out-data"])
data = inner["data"]
if data.get("state") != "running" or not data.get("supported"):
    raise SystemExit("Home Assistant is not running and supported")
print(
    "HAOS {}, Supervisor {}, Core {}".format(
        data["hassos"], data["supervisor"], data["homeassistant"]
    )
)
'
)" || die "Home Assistant health preflight failed"

"$check_only" && {
  log "HAOS backup preflight passed ($ha_info)"
  exit 0
}

install -d -m 0700 "$HAOS_VM_BACKUP_DIR"
staging_dir="$(mktemp -d "$HAOS_VM_BACKUP_DIR/.staging.XXXXXXXX")"
cleanup() {
  rm -rf -- "$staging_dir"
}
trap cleanup EXIT INT TERM

log "Creating full VM $HAOS_VMID snapshot backup ($ha_info)"
vzdump "$HAOS_VMID" \
  --mode snapshot \
  --dumpdir "$staging_dir" \
  --compress zstd \
  --notes-template "Managed HAOS recovery image: $ha_info"

shopt -s nullglob
archives=("$staging_dir"/vzdump-qemu-"$HAOS_VMID"-*.vma.zst)
shopt -u nullglob
((${#archives[@]} == 1)) ||
  die "Expected exactly one VM archive, found ${#archives[@]}"
archive="${archives[0]}"

log "Verifying compressed stream and VMA structure"
zstd -t "$archive"
zstdcat "$archive" | vma verify -

archive_name="$(basename -- "$archive")"
checksum="$staging_dir/$archive_name.sha256"
(
  cd -- "$staging_dir"
  sha256sum "$archive_name" >"$archive_name.sha256"
)
chmod 0600 "$archive" "$checksum"

target="$HAOS_VM_BACKUP_DIR/$archive_name"
target_checksum="$target.sha256"
[[ ! -e "$target" && ! -e "$target_checksum" ]] ||
  die "Refusing to overwrite an existing recovery image: $target"
mv -- "$archive" "$target"
mv -- "$checksum" "$target_checksum"

log "Verified HAOS recovery image stored at $target"
log "Older recovery images are retained; cleanup requires a separate reviewed task."
