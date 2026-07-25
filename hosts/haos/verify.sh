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

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

for command_name in curl python3 qm sha256sum tar; do
  command -v "$command_name" >/dev/null ||
    fail "required command is missing: $command_name"
done

qm status "$HAOS_VMID" | grep -q 'status: running' ||
  fail "HAOS VM $HAOS_VMID is not running"
config="$(qm config "$HAOS_VMID")"
for expected in \
  "name: $HAOS_VM_NAME" \
  "agent: 1" \
  "bios: $HAOS_BIOS" \
  "cores: $HAOS_CORES" \
  "cpu: $HAOS_CPU_TYPE" \
  "memory: $HAOS_MEMORY" \
  "onboot: 1" \
  "protection: 1" \
  "scsihw: $HAOS_SCSIHW" \
  "startup: $HAOS_STARTUP"; do
  grep -qx "$expected" <<<"$config" ||
    fail "HAOS VM $HAOS_VMID does not match declared setting $expected"
done
grep -qE \
  "^net0: .*(virtio|macaddr)=${HAOS_MAC}([,]|).*bridge=${PVE_BRIDGE}([,]|$)" \
  <<<"$config" ||
  fail "HAOS VM bridge or MAC address drifted"
grep -qE \
  "^scsi0: ${HAOS_VM_STORAGE}:.*[,]size=${HAOS_DISK_GB}G(,|$)" \
  <<<"$config" ||
  fail "HAOS VM disk storage or size drifted"

qm agent "$HAOS_VMID" ping >/dev/null ||
  fail "HAOS VM guest agent is unavailable"
qm guest exec "$HAOS_VMID" -- ha info --raw-json |
  python3 -c '
import json
import sys
outer = json.load(sys.stdin)
inner = json.loads(outer["out-data"])
data = inner["data"]
if data.get("state") != "running":
    raise SystemExit("Home Assistant Core is not running")
if not data.get("supported"):
    raise SystemExit("Home Assistant reports an unsupported installation")
if data.get("channel") != "stable":
    raise SystemExit("Home Assistant is not on the stable channel")
print(
    "OK   HAOS {}; Supervisor {}; Core {}".format(
        data["hassos"], data["supervisor"], data["homeassistant"]
    )
)
'
qm guest exec "$HAOS_VMID" -- ha core check --no-progress >/dev/null ||
  fail "Home Assistant configuration validation failed"
qm guest exec "$HAOS_VMID" -- grep -Eq \
  '^[[:space:]]*-[[:space:]]*192\.168\.0\.110[[:space:]]*$' \
  /mnt/data/supervisor/homeassistant/configuration.yaml |
  python3 -c '
import json
import sys
result = json.load(sys.stdin)
raise SystemExit(result.get("exitcode", 1))
' ||
  fail "Home Assistant does not trust Nginx Proxy Manager at 192.168.0.110"
[[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --max-time 10 "http://$HAOS_IP:8123/")" == "200" ]] ||
  fail "Home Assistant LAN UI did not return HTTP 200"
[[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --max-time 15 "https://ha.rafael.media/")" == "200" ]] ||
  fail "Home Assistant HTTPS proxy did not return HTTP 200"

mapfile -t vm_archives < <(
  find "$HAOS_VM_BACKUP_DIR" -maxdepth 1 -type f \
    -name "vzdump-qemu-${HAOS_VMID}-*.vma.zst" -printf '%T@ %p\n' |
    sort -nr |
    cut -d' ' -f2-
)
((${#vm_archives[@]} > 0)) ||
  fail "no canonical VM recovery image exists"
latest_vm_archive="${vm_archives[0]}"
[[ -s "$latest_vm_archive.sha256" ]] ||
  fail "VM recovery image checksum sidecar is missing"
(
  cd -- "$HAOS_VM_BACKUP_DIR"
  sha256sum --check "$(basename -- "$latest_vm_archive.sha256")"
) >/dev/null || fail "VM recovery image checksum failed"

mapfile -t native_backups < <(
  find "$HAOS_NATIVE_BACKUP_DIR" -maxdepth 1 -type f \
    -name 'haos-*.tar' -printf '%T@ %p\n' |
    sort -nr |
    cut -d' ' -f2-
)
((${#native_backups[@]} > 0)) ||
  fail "no exported protected Home Assistant backup exists"
latest_native_backup="${native_backups[0]}"
[[ "$(stat -c '%a' "$latest_native_backup")" == "600" ]] ||
  fail "native Home Assistant backup is not mode 0600"
tar -tf "$latest_native_backup" >/dev/null ||
  fail "native Home Assistant backup archive is unreadable"

printf 'OK   VM %s is healthy; verified VM and native recovery artifacts exist\n' \
  "$HAOS_VMID"
