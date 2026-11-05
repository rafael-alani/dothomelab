#!/usr/bin/env bash
set -Eeuo pipefail
readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ $EUID -eq 0 ]] || { echo 'Run as root on PVE or a managed Debian guest' >&2; exit 1; }
install -m 0644 "$script_dir/99-dothomelab-unattended" /etc/apt/apt.conf.d/99-dothomelab-unattended
if ! command -v unattended-upgrade >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends unattended-upgrades
fi
# Package defaults must not create a second, un-gated installer schedule.
systemctl disable --now apt-daily-upgrade.timer
echo 'Routine Debian/Proxmox updates configured; reboot and package removal remain disabled.'
