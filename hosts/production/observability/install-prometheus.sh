#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export BLOG_SOURCE_ROOT="$(cd "$here/../../.." && pwd)"
[[ "$(hostname -s)" == apps ]] || exit 1
python3 "$here/configure.py"
image="$(docker inspect prometheus --format '{{.Config.Image}}')"
[[ "$image" == prom/prometheus:v3.13.1 ]] || { echo 'Prometheus version drifted; review first'; exit 1; }
docker run --rm --network none --entrypoint /bin/promtool \
  -v "$BLOG_SOURCE_ROOT/hosts/apps/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$BLOG_SOURCE_ROOT/hosts/staging/blog-observability:/etc/prometheus/blog:ro" \
  -v /srv/appdata/docker/production-monitoring:/etc/prometheus/production:ro \
  "$image" check config /etc/prometheus/prometheus.yml
docker run --rm --network none --entrypoint /bin/promtool \
  -v "$here:/rules:ro" -w /rules "$image" test rules alerts.test.yml
compose=(docker compose --env-file /dev/null -f "$BLOG_SOURCE_ROOT/hosts/apps/prometheus/compose.yaml" -f "$here/prometheus.override.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-deps --pull never --wait --wait-timeout 90 prometheus
curl -fsS -o /dev/null http://192.168.0.112:9090/-/ready
