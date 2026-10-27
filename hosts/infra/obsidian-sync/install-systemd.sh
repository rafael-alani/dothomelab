#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

[[ $# -eq 0 ]] || {
  echo "Usage: $0" >&2
  exit 2
}

exec 9>/run/lock/dothomelab-proton-backup.lock
flock --nonblock 9 || { echo "A Proton backup is running; retry installation later" >&2; exit 1; }
python3 "$project_dir/backup-runtime.py" install

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
