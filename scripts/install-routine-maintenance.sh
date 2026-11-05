#!/usr/bin/env bash
set -Eeuo pipefail
readonly repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_root/provision/inventory.env"
[[ $EUID -eq 0 ]] || { echo 'Run on PVE as root' >&2; exit 1; }
bash "$repo_root/hosts/common/install-os-updates.sh"
for ctid in "${ALL_CTIDS[@]}"; do
  destination=/usr/local/lib/dothomelab-maintenance
  pct exec "$ctid" -- install -d -m 0755 "$destination"
  pct push "$ctid" "$repo_root/hosts/common/99-dothomelab-unattended" "$destination/99-dothomelab-unattended" --perms 0644
  pct push "$ctid" "$repo_root/hosts/common/install-os-updates.sh" "$destination/install-os-updates.sh" --perms 0755
  pct exec "$ctid" -- bash "$destination/install-os-updates.sh"
  if [[ "$ctid" == 114 || "$ctid" == 115 ]]; then
    pct push "$ctid" "$repo_root/scripts/cleanup-runtime.py" "$destination/cleanup-runtime.py" --perms 0755
  fi
done
install -m 0755 "$repo_root/backup/pbs/os-update.sh" /usr/local/sbin/dothomelab-os-update
install -m 0644 "$repo_root/provision/inventory.env" /etc/dothomelab/inventory.env
install -m 0644 "$repo_root/backup/pbs/dothomelab-wud-update.service" /etc/systemd/system/
systemctl daemon-reload
echo 'Routine maintenance installed; only a successful scheduled backup starts it.'
