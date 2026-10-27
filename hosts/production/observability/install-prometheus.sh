#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
[[ "$(hostname -s)" == infra ]] || { echo 'Run on CT110'; exit 1; }
python3 "$here/configure.py"
bash "$root/hosts/infra/observability/validate.sh"
compose=(docker compose --env-file /dev/null -f "$root/hosts/infra/prometheus/compose.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-deps --pull never --wait --wait-timeout 90 prometheus
curl -fsS -o /dev/null http://192.168.0.110:9090/-/ready
