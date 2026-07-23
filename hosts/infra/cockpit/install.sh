#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify the guest OS" >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "debian" || "${VERSION_CODENAME:-}" != "bookworm" ]]; then
  echo "This installer expects Debian 12 (bookworm)" >&2
  exit 1
fi

install -m 0644 /dev/stdin /etc/apt/sources.list.d/bookworm-backports.list <<'EOF'
deb http://deb.debian.org/debian bookworm-backports main
EOF

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y -t bookworm-backports \
  cockpit \
  cockpit-system

install -m 0644 \
  "$(dirname "$0")/dothomelab-pihole-ip.service" \
  /etc/systemd/system/dothomelab-pihole-ip.service

systemctl daemon-reload
systemctl enable --now cockpit.socket

echo "Cockpit is active. Enable dothomelab-pihole-ip.service only at DNS cutover."
