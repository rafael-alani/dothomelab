#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$(hostname -s)" == production ]] || { echo 'Run inside production CT115' >&2; exit 1; }
mountpoint -q /srv/appdata/docker/production
install -d -m 0700 /var/lib/dothomelab-production /srv/appdata/docker/production/blog
install -d -m 0700 /srv/appdata/docker/production/blog/releases /srv/appdata/docker/production/observability
if [[ ! -d /var/log/journal ]]; then
  install -d -m 2755 -o root -g systemd-journal /var/log/journal
  journalctl --flush
fi
# No timer, service, web container, collector, or public route is activated here.
echo 'Production runtime scaffold prepared; application remains operator-activated'
