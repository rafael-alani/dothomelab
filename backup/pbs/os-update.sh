#!/usr/bin/env bash
# Executed before WUD by the successful scheduled-backup handoff, never a timer.
set -Eeuo pipefail
readonly mode="${1:---apply}"
[[ "$mode" == --apply || "$mode" == --dry-run ]] || { echo 'Usage: os-update.sh [--dry-run|--apply]' >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo 'Run on PVE as root' >&2; exit 1; }
source /etc/dothomelab/inventory.env
exec 9>/run/lock/dothomelab-os-update.lock
flock -n 9 || { echo 'Another routine OS update is active' >&2; exit 1; }
args=()
if [[ "$mode" == --dry-run || "${WUD_UPDATE_DRY_RUN:-false}" == true ]]; then args+=(--dry-run); fi
for ctid in "${ALL_CTIDS[@]}"; do
  pct status "$ctid" | grep -q 'status: running' || { echo "Required CT$ctid is stopped" >&2; exit 1; }
  pct exec "$ctid" -- test -f /etc/apt/apt.conf.d/99-dothomelab-unattended
  pct exec "$ctid" -- test -x /usr/bin/unattended-upgrade
done
test -f /etc/apt/apt.conf.d/99-dothomelab-unattended
for ctid in "${ALL_CTIDS[@]}"; do
  echo "Routine OS updates: CT$ctid"
  pct exec "$ctid" -- apt-get update -qq
  pct exec "$ctid" -- env DEBIAN_FRONTEND=noninteractive unattended-upgrade "${args[@]}"
done
echo 'Routine OS updates: PVE'
apt-get update -qq
DEBIAN_FRONTEND=noninteractive unattended-upgrade "${args[@]}"
for ctid in 114 115; do
  cleanup_args=(--prune-build-cache 5GB)
  if ((${#args[@]} == 0)); then cleanup_args+=(--apply); fi
  echo "Bounded unused build-cache cleanup: CT$ctid (5GB target; no image or volume pruning)"
  pct exec "$ctid" -- python3 /usr/local/lib/dothomelab-maintenance/cleanup-runtime.py "${cleanup_args[@]}"
done
echo "OS update pass complete; running PVE kernel: $(uname -r)"
if [[ -s /var/run/reboot-required ]]; then
  echo 'ACTION REQUIRED: a PVE reboot is pending; request explicit authorization.'
fi
# Proxmox does not always create Debian's reboot marker.
if command -v proxmox-boot-tool >/dev/null; then proxmox-boot-tool kernel list; fi
