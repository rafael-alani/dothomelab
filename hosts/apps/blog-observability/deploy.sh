#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_root="$(cd "$here/../../.." && pwd)"
[[ "$(hostname -s)" == apps ]] || { echo 'Run in CT112' >&2; exit 1; }
[[ $# -eq 0 || ( $# -eq 1 && "$1" == --pull ) ]] || { echo 'Usage: deploy.sh [--pull]' >&2; exit 2; }
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/blog-observability)" == rpool/appdata/docker ]] || {
  echo 'Canonical appdata mount is required' >&2; exit 1;
}
# A restored legacy installation must be migrated, never silently replaced by an empty service.
if [[ -s /srv/appdata/docker/staging/blog-observability/postgres/PG_VERSION &&
      ! -s /srv/appdata/docker/blog-observability/postgres/PG_VERSION ]]; then
  echo 'Legacy Umami state requires the reviewed migration before deployment' >&2; exit 1
fi
export BLOG_OBSERVABILITY_COMMIT="$(cat "$source_root/DEPLOYED_COMMIT")"
compose=(docker compose --env-file /srv/appdata/docker/blog-observability/runtime.env -f "$here/compose.yaml")
"${compose[@]}" config --quiet
# Clean recovery can fetch the exact declared digests; migration uses already verified local images.
if [[ "${1:-}" == --pull ]]; then "${compose[@]}" pull; fi
"${compose[@]}" up -d --pull never --wait --wait-timeout 180
python3 "$source_root/hosts/staging/blog-observability/initialize-umami.py"
curl -fsS -o /dev/null http://192.168.0.112:8091/api/health
echo 'Umami and Grafana are ready on Apps; end-to-end verification remains required'
