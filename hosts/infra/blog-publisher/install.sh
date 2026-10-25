#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$(hostname -s)" == infra ]] || { echo 'Run inside Infra CT110' >&2; exit 1; }
findmnt -T /vault/shared/media/obsidian >/dev/null
findmnt -T /srv/appdata/docker/staging >/dev/null
# Only create the dedicated output directory; preserve all existing data and permissions.
if [[ ! -d /srv/appdata/docker/staging/blog/editorial ]]; then
  install -d -o 1000 -g 1000 -m 0700 /srv/appdata/docker/staging/blog/editorial
fi
docker compose -f "$here/compose.yaml" config --quiet
docker compose -f "$here/compose.yaml" build
install -m 0644 "$here/dothomelab-blog-publisher.service" /etc/systemd/system/
install -m 0644 "$here/dothomelab-blog-publisher.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dothomelab-blog-publisher.timer
