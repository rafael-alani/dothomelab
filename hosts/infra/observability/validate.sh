#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
env_file="${1:-/srv/appdata/docker/observability/runtime.env}"
for file in "$here/compose.yaml" "$here/../prometheus/compose.yaml" "$here/../loki/compose.yaml"; do
  docker compose --env-file "$env_file" -f "$file" config --quiet
done
docker run --rm --network none --entrypoint /bin/promtool \
  -v "$here/../prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$root/hosts/staging/blog-observability:/etc/prometheus/blog:ro" \
  -v /srv/appdata/docker/production-monitoring:/etc/prometheus/production:ro \
  -v "$here/fleet-alerts.yml:/etc/prometheus/fleet-alerts.yml:ro" \
  -v "$here/targets.json:/etc/prometheus/targets.json:ro" \
  prom/prometheus:v3.13.1 check config /etc/prometheus/prometheus.yml
for folder in "$root/hosts/staging/blog-observability" "$root/hosts/production/observability"; do
  docker run --rm --network none --entrypoint /bin/promtool \
    -v "$folder:/rules:ro" -w /rules prom/prometheus:v3.13.1 test rules alerts.test.yml
done
docker run --rm --network none -v "$here/../loki/loki-config.yaml:/etc/loki/config.yml:ro" \
  grafana/loki:3.7.3 -config.file=/etc/loki/config.yml -verify-config=true
for config in "$here/fleet.alloy" "$root/hosts/staging/blog-observability/config.alloy" "$root/hosts/production/observability/config.alloy"; do
  docker run --rm --network none -v "$config:/config.alloy:ro" grafana/alloy:v1.21.1 validate /config.alloy
done
docker run --rm --network none -v "$here/blackbox.yml:/config.yml:ro" \
  prom/blackbox-exporter:v0.29.1 --config.file=/config.yml --config.check
