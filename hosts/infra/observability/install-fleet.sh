#!/usr/bin/env bash
# PVE: no guest agents or additional service credentials are installed.
set -Eeuo pipefail
[[ $EUID == 0 && -d /etc/pve ]] || { echo 'Run on PVE as root'; exit 1; }
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_root="$(cd "$here/../../.." && pwd)"
[[ -s "$source_root/DEPLOYED_COMMIT" ]] || { echo 'Use a retained committed source archive'; exit 1; }
install -d -m 0755 /opt/dothomelab-observability
ln -sfn "$source_root" /opt/dothomelab-observability/current
install -m 0644 "$here"/dothomelab-observability-fleet.{service,timer} /etc/systemd/system/
systemctl daemon-reload
systemctl start dothomelab-observability-fleet.service
systemctl enable --now dothomelab-observability-fleet.timer
