#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$(hostname -s)" == staging ]] || { echo 'Run in CT114' >&2; exit 1; }
mountpoint -q /srv/appdata/docker/staging
if [[ ! -d /var/log/journal ]]; then
  install -d -m 2755 -o root -g systemd-journal /var/log/journal
  journalctl --flush
fi
env_file=/srv/appdata/docker/staging/blog-observability/runtime.env
export BLOG_OBSERVABILITY_COMMIT="$(cat "$here/../../../DEPLOYED_COMMIT")"
compose=(docker compose --env-file "$env_file" -f "$here/compose.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --wait --wait-timeout 180
for attempt in {1..30}; do
  if curl -fsS -o /dev/null http://192.168.0.114:8090/api/heartbeat; then break; fi
  sleep 2
done
python3 "$here/initialize-umami.py"
curl -fsS -o /dev/null http://192.168.0.114:8091/api/health
curl -fsS -o /dev/null http://192.168.0.114:12345/-/ready
echo 'Blog observability stack is ready; readership and log ingestion require end-to-end verification'
