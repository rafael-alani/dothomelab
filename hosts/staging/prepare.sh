#!/usr/bin/env bash
set -Eeuo pipefail
readonly here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$(hostname -s)" == staging ]] || { echo 'Run inside staging CT114' >&2; exit 1; }
mountpoint -q /srv/appdata/docker/staging
install -d -m 0700 /var/lib/dothomelab-staging /srv/appdata/docker/staging
install -m 0644 "$here/dothomelab-staging.service" /etc/systemd/system/
install -m 0644 "$here/dothomelab-staging.timer" /etc/systemd/system/
systemctl daemon-reload
# First deployment and verification happen before the timer is enabled.
