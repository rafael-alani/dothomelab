#!/usr/bin/env bash
# Read-only revision check, also usable independently before activation.
set -Eeuo pipefail
repo="$1"
# Keep the activation code and its shared imports together; other services and
# documentation can advance without reinstalling an identical scaffold.
paths=(hosts/production hosts/staging/editorial.py hosts/common/dotenv.py
  hosts/infra/observability/initialize-umami.py
  hosts/infra/observability/grafana/dashboards/blog.json
  ':(exclude)hosts/production/README.md' ':(exclude)hosts/production/test_*.py')
for guest in 115 110; do
  marker=/opt/dothomelab-production/current/DEPLOYED_COMMIT
  [[ "$guest" != 115 ]] || marker=/opt/dothomelab/DEPLOYED_COMMIT
  deployed="$(pct exec "$guest" -- cat "$marker")"
  if [[ ! "$deployed" =~ ^[0-9a-f]{40}$ ]] ||
     ! git -C "$repo" cat-file -e "$deployed^{commit}" 2>/dev/null ||
     ! git -C "$repo" diff --quiet "$deployed" -- "${paths[@]}"; then
    echo "Production runtime on CT$guest differs from this checkout or its revision is unavailable; reconcile before activation" >&2
    exit 1
  fi
done
