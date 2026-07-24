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

install -o root -g root -m 0755 \
  "$project_dir/backup-runner.sh" \
  /usr/local/sbin/dothomelab-obsidian-proton-backup
install -o root -g root -m 0644 \
  "$project_dir/systemd/dothomelab-obsidian-proton-backup.service" \
  /etc/systemd/system/dothomelab-obsidian-proton-backup.service
install -o root -g root -m 0644 \
  "$project_dir/systemd/dothomelab-obsidian-proton-backup.timer" \
  /etc/systemd/system/dothomelab-obsidian-proton-backup.timer

systemctl daemon-reload

if [[ "$enable_timer" == true ]]; then
  systemctl enable --now dothomelab-obsidian-proton-backup.timer
  echo "Installed and enabled the daily Obsidian Proton backup timer"
else
  echo "Installed the timer disabled; enable it only after Proton login succeeds"
fi
