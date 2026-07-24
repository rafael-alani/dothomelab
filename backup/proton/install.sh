#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
enable_timer=false

if [[ "${1:-}" == "--enable" ]]; then
  enable_timer=true
elif [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--enable]" >&2
  exit 2
fi

[[ $EUID -eq 0 ]] || {
  echo "Run this installer as root on the PVE host" >&2
  exit 1
}
command -v pct >/dev/null || {
  echo "pct is required; run this installer on the PVE host" >&2
  exit 1
}
pct exec 110 -- test -x /usr/local/sbin/dothomelab-proton-backup-runner || {
  echo "Install the Infra Proton runner before the PVE units" >&2
  exit 1
}

if [[ "$enable_timer" == true ]]; then
  for dataset in obsidian photos environment; do
    cycle_file="/srv/appdata/docker/proton-drive/sources/$dataset/last-success.cycle"
    [[ -s "$cycle_file" ]] || {
      echo "Refusing to enable: $dataset has no checksum-verified generation" >&2
      exit 1
    }
  done
fi

install -o root -g root -m 0755 \
  "$project_dir/fortnightly-backup.sh" \
  /usr/local/sbin/dothomelab-proton-backup
install -o root -g root -m 0644 \
  "$project_dir/dothomelab-proton-backup.service" \
  "$project_dir/dothomelab-proton-backup.timer" \
  /etc/systemd/system/
systemctl daemon-reload

if [[ "$enable_timer" == true ]]; then
  systemctl enable --now dothomelab-proton-backup.timer
  echo "Installed and enabled the daily due-check for fortnightly Proton backups"
elif systemctl is-enabled dothomelab-proton-backup.timer >/dev/null 2>&1; then
  echo "Installed the PVE Proton units and preserved the enabled timer"
else
  echo "Installed the PVE Proton units; the timer remains disabled until first-run verification"
fi
