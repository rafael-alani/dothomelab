#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export BLOG_SOURCE_ROOT="$(cd "$here/../../.." && pwd)"
[[ "$(hostname -s)" == apps ]] || { echo 'Run inside Apps CT112' >&2; exit 1; }
python3 "$BLOG_SOURCE_ROOT/hosts/production/observability/configure.py" --files-only
image="$(docker inspect prometheus --format '{{.Config.Image}}')"
[[ "$image" == prom/prometheus:v3.13.1 ]] || { echo 'Unexpected Prometheus version; review before reconfiguring' >&2; exit 1; }
docker run --rm --network none --entrypoint /bin/promtool \
  -v "$BLOG_SOURCE_ROOT/hosts/apps/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$here:/etc/prometheus/blog:ro" \
  -v /srv/appdata/docker/production-monitoring:/etc/prometheus/production:ro "$image" check config /etc/prometheus/prometheus.yml
docker run --rm --network none --entrypoint /bin/promtool \
  -v "$here:/etc/prometheus/blog:ro" -w /etc/prometheus/blog \
  "$image" test rules alerts.test.yml
compose=(docker compose --env-file /dev/null \
  -f /opt/dothomelab/hosts/apps/prometheus/compose.yaml \
  -f "$here/prometheus.override.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-deps --pull never --wait --wait-timeout 90 prometheus
curl -fsS -o /dev/null http://192.168.0.112:9090/-/ready
echo 'Prometheus blog configuration installed; existing TSDB and image retained'
