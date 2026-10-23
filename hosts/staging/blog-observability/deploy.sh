#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$(hostname -s)" == staging ]] || { echo 'Run in CT114' >&2; exit 1; }
mountpoint -q /srv/appdata/docker/staging
if [[ ! -d /var/log/journal ]]; then
  install -d -m 2755 -o root -g systemd-journal /var/log/journal
  journalctl --flush
fi
export BLOG_OBSERVABILITY_COMMIT="$(cat "$here/../../../DEPLOYED_COMMIT")"
compose=(docker compose --env-file /dev/null -f "$here/compose.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --wait --wait-timeout 180
curl -fsS -o /dev/null http://192.168.0.114:12345/-/ready
echo 'Blog collectors are ready; log ingestion requires end-to-end verification'
