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

guest_exec_succeeded() {
  python3 -c '
import json
import sys

result = json.load(sys.stdin)
raise SystemExit(result.get("exitcode", 1))
'
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
qm guest exec "$HAOS_VMID" -- ha core check --no-progress |
  guest_exec_succeeded ||
  fail "Home Assistant configuration validation failed"
qm guest exec "$HAOS_VMID" -- grep -Eq \
  '^[[:space:]]*-[[:space:]]*192\.168\.0\.110[[:space:]]*$' \
  /mnt/data/supervisor/homeassistant/configuration.yaml |
  guest_exec_succeeded ||
  fail "Home Assistant does not trust Nginx Proxy Manager at 192.168.0.110"

govee_app_check='
ha apps info b9845f46_govee2mqtt --raw-json |
  jq -e "
    .data.state == \"started\" and
    .data.auto_update == true and
    .data.options.temperature_scale == \"C\" and
    (.data.options.govee_api_key | type == \"string\" and length >= 16) and
    (.data.options | has(\"govee_email\") | not) and
    (.data.options | has(\"govee_password\") | not)
  " >/dev/null
'
qm guest exec "$HAOS_VMID" -- /bin/bash -lc "$govee_app_check" |
  guest_exec_succeeded ||
  fail "Govee2MQTT is not running with the accepted credential policy"

govee_device_check='
curl -fsS http://127.0.0.1:8056/api/devices |
  jq -e "
    (([.[] | select(.sku == \"H60A1\" or .sku == \"H6072\") | .sku] |
      sort) == ([\"H60A1\", \"H60A1\", \"H6072\"] | sort)) and
    (([.[].sku] | sort) ==
      ([\"BaseGroup\", \"H6072\", \"H60A1\", \"H60A1\",
        \"SameModeGroup\", \"SameModeGroup\", \"SameModeGroup\",
        \"SameModeGroup\"] | sort))
  " >/dev/null
'
qm guest exec "$HAOS_VMID" -- docker exec addon_b9845f46_govee2mqtt \
  sh -c "$govee_device_check" |
  guest_exec_succeeded ||
  fail "Govee2MQTT did not discover exactly two H60A1 and one H6072"

govee_registry_check='
import json
import yaml

with open("/config/.storage/core.device_registry", encoding="utf-8") as source:
    devices = json.load(source)["data"]["devices"]
with open("/config/.storage/core.entity_registry", encoding="utf-8") as source:
    entities = json.load(source)["data"]["entities"]
with open("/config/scenes.yaml", encoding="utf-8") as source:
    scenes = yaml.safe_load(source) or []

govee_devices = [
    device
    for device in devices
    if any(
        identifier[0] == "mqtt"
        and (
            identifier[1] == "gv2mqtt"
            or identifier[1].startswith("gv2mqtt-")
        )
        for identifier in device.get("identifiers", [])
    )
]
physical_devices = [
    device
    for device in govee_devices
    if device.get("model") in {"H60A1", "H6072"}
]
assert sorted(device.get("model") for device in physical_devices) == [
    "H6072",
    "H60A1",
    "H60A1",
]
assert len(
    [device for device in govee_devices if device.get("model") == "govee2mqtt"]
) == 1
assert all(
    device.get("model") in {
        "BaseGroup",
        "H6072",
        "H60A1",
        "SameModeGroup",
        "govee2mqtt",
    }
    for device in govee_devices
)
virtual_devices = [
    (
        device.get("name_by_user") or device.get("name"),
        device.get("model"),
    )
    for device in govee_devices
    if device.get("model") in {"BaseGroup", "SameModeGroup"}
]
assert sorted(virtual_devices) == [
    ("All", "BaseGroup"),
    ("Bed", "SameModeGroup"),
    ("Ceiling", "SameModeGroup"),
    ("Desk", "SameModeGroup"),
    ("Floor", "SameModeGroup"),
]

physical_ids = {
    device["id"]
    for device in physical_devices
}
physical_lights = [
    entity
    for entity in entities
    if entity.get("device_id") in physical_ids
    and entity["entity_id"].startswith("light.")
]
assert len(physical_lights) == 37
assert {
    "light.bed_light",
    "light.desk_light",
    "light.rgbicww_floor_lamp_2",
}.issubset({entity["entity_id"] for entity in physical_lights})

assert len(scenes) >= 39
for scene in scenes:
    state = scene.get("entities", {}).get("light.rgbicww_floor_lamp_2")
    if isinstance(state, dict):
        assert state.get("effect") != "Fireplace"
'
qm guest exec "$HAOS_VMID" -- docker exec homeassistant \
  python -c "$govee_registry_check" |
  guest_exec_succeeded ||
  fail "Home Assistant has stale Govee devices, missing segments, or invalid scenes"

govee_effect_check='
set -eu
for entity in light.bed_light light.desk_light; do
  curl -fsS \
    -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
    "http://supervisor/core/api/states/$entity" |
    jq -e "
      (.attributes.effect_list | length) >= 70 and
      (.attributes.effect_list | index(\"Forest\") != null) and
      (.attributes.effect_list | index(\"Meditation\") != null) and
      (.attributes.effect_list | index(\"Fire\") != null)
    " >/dev/null
done
curl -fsS \
  -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  http://supervisor/core/api/states/light.rgbicww_floor_lamp_2 |
  jq -e "
    (.attributes.effect_list | length) >= 65 and
    (.attributes.effect_list | index(\"Fire\") != null)
  " >/dev/null
'
qm guest exec "$HAOS_VMID" -- docker exec addon_core_configurator \
  sh -c "$govee_effect_check" |
  guest_exec_succeeded ||
  fail "The rebuilt Govee lights are missing effect catalogs required by saved scenes"

[[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --max-time 10 "http://$HAOS_IP:8056/assets/index.html")" == "200" ]] ||
  fail "Govee2MQTT LAN UI did not return HTTP 200"
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
