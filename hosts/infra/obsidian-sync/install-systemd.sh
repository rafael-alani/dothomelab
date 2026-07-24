#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

[[ $# -eq 0 ]] || {
  echo "Usage: $0" >&2
  exit 2
}

install -o root -g root -m 0755 \
  "$project_dir/backup-runner.sh" \
  /usr/local/sbin/dothomelab-proton-backup-runner

# Scheduling moved to the PVE host because only the host should read
# /root/.env. Remove the obsolete guest timer/service so two schedulers cannot
# race or run a backup without the ephemeral environment staging file.
systemctl disable --now dothomelab-obsidian-proton-backup.timer \
  >/dev/null 2>&1 || true
rm -f -- \
  /etc/systemd/system/dothomelab-obsidian-proton-backup.timer \
  /etc/systemd/system/dothomelab-obsidian-proton-backup.service \
  /usr/local/sbin/dothomelab-obsidian-proton-backup
systemctl daemon-reload

echo "Installed the Infra Proton runner; scheduling is owned by the PVE host"
