#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$here/../../provision/inventory.env"
config="$(pct config 115)"
for value in 'hostname: production' 'unprivileged: 1' 'features: nesting=1' 'onboot: 1' \
  "cores: ${CT_CORES[115]}" "memory: ${CT_MEMORY[115]}" \
  "mp0: $PRODUCTION_APPDATA_HOST_PATH,mp=$PRODUCTION_APPDATA_GUEST_PATH"; do
  grep -Fqx "$value" <<<"$config"
done
grep -qE "^rootfs: ${PVE_ROOTFS_STORAGE}:.*[,]size=${CT_ROOTFS_GB[115]}G(,|$)" <<<"$config"
grep -Fq "ip=${CT_IP[115]}/$LAN_PREFIX" <<<"$config"
! grep -qE '^(mp([1-9][0-9]*)|dev[0-9]+):' <<<"$config"
[[ "$(findmnt -n -o SOURCE -T "$PRODUCTION_APPDATA_HOST_PATH")" == "$APPDATA_DATASET" ]]
pct exec 115 -- mountpoint -q "$PRODUCTION_APPDATA_GUEST_PATH"
pct exec 115 -- docker info >/dev/null
! pct exec 115 -- ss -ltn | grep -qE ':237[56][[:space:]]'
! pct exec 115 -- systemctl list-unit-files --no-legend | grep -E 'dothomelab-(production|staging).*timer'
grep -E '^QUIESCE_CTIDS="[0-9 ]*115([ "]|$)' /etc/dothomelab/pbs-appdata.conf >/dev/null
pct exec 115 -- python3 /opt/dothomelab/hosts/production/release.py --check
printf 'CT115 SSD, narrow mount, Docker, backup inclusion and dependency checks passed\n'
