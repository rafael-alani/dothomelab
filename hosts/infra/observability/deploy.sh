#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_root="$(cd "$here/../../.." && pwd)"
[[ "$(hostname -s)" == infra ]] || { echo 'Run in CT110' >&2; exit 1; }
[[ $# -eq 0 || ( $# -eq 1 && "$1" == --pull ) ]] || { echo 'Usage: deploy.sh [--pull]' >&2; exit 2; }
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/observability)" == rpool/appdata/docker ]] || {
  echo 'Canonical appdata mount is required' >&2; exit 1;
}
# A restored legacy installation must be migrated, never silently replaced by an empty service.
if [[ -s /srv/appdata/docker/blog-observability/postgres/PG_VERSION &&
      ! -s /srv/appdata/docker/observability/postgres/PG_VERSION ]]; then
  echo 'Legacy Umami state requires the reviewed migration before deployment' >&2; exit 1
fi
export BLOG_OBSERVABILITY_COMMIT="$(cat "$source_root/DEPLOYED_COMMIT")"
compose=(docker compose --env-file /srv/appdata/docker/observability/runtime.env -f "$here/compose.yaml")
"${compose[@]}" config --quiet
# Clean recovery can fetch the exact declared digests; migration uses already verified local images.
if [[ "${1:-}" == --pull ]]; then "${compose[@]}" pull; fi
bash "$here/validate.sh"
"${compose[@]}" up -d --pull never --wait --wait-timeout 180
python3 "$source_root/hosts/production/observability/configure.py" --files-only
python3 "$source_root/hosts/infra/observability/initialize-umami.py"
curl -fsS -o /dev/null http://192.168.0.110:8091/api/health
python3 "$source_root/hosts/production/observability/configure.py"
# Routing is reconciled separately after data and collector acceptance.
echo 'Umami and Grafana are ready on Infra; end-to-end verification remains required'
