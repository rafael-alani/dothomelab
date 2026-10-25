#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$(hostname -s)" == staging ]] || exit 1
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
compose=(docker compose --env-file /dev/null \
  -f /opt/dothomelab/hosts/staging/blog-observability/compose.yaml \
  -f "$here/staging-blackbox.override.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-deps --pull never --wait --wait-timeout 90 blackbox
