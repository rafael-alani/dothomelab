#!/usr/bin/env bash
# This command is the publication boundary. Agents need an explicit user request.
set -Eeuo pipefail
[[ $# == 2 && "$1" == blog && "$2" == --publish-rafael-ink ]] || {
  echo 'Usage (explicit production authorization required): hosts/production/activate.sh blog --publish-rafael-ink' >&2; exit 2;
}
[[ $EUID == 0 && -d /etc/pve ]] || { echo 'Run on PVE as root'; exit 1; }
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
exec 9>/run/lock/dothomelab-production-activation.lock
flock -n 9
bash "$repo/hosts/production/check-scaffold.sh" "$repo"
# Validate branch/dependencies and build before changing the currently served route.
pct exec 115 -- python3 /opt/dothomelab/hosts/production/release.py --check
pct exec 110 -- python3 /opt/dothomelab-production/current/hosts/production/configure-route.py
python3 "$repo/hosts/production/prepare-content.py"
pct exec 115 -- python3 /opt/dothomelab/hosts/production/release.py --prepare
pct exec 115 -- python3 /opt/dothomelab/hosts/production/release.py --activate
pct exec 115 -- bash -eu -c '
  here=/opt/dothomelab/hosts/production/observability
  export PRODUCTION_PLATFORM_COMMIT="$(cat /opt/dothomelab/DEPLOYED_COMMIT)"
  install -d -m 0700 /srv/appdata/docker/production/observability/alloy
  docker compose --env-file /dev/null -f "$here/compose.yaml" config --quiet
  docker compose --env-file /dev/null -f "$here/compose.yaml" up -d --wait --wait-timeout 120
  curl --retry 10 --retry-connrefused --retry-delay 1 --max-time 5 -fsS -o /dev/null http://192.168.0.115:12345/-/ready
'
# Existing apex DNS/certificate are retained. This switches only the existing route.
pct exec 110 -- python3 /opt/dothomelab-production/current/hosts/production/configure-route.py --publish-rafael-ink
for path in / /about /feed.xml /sitemap.xml /telemetry/script.js; do
  curl --fail --silent --show-error --resolve rafael.ink:443:192.168.0.110 "https://rafael.ink$path" -o /dev/null
done
pct exec 110 -- python3 /opt/dothomelab-production/current/hosts/production/observability/configure.py --activate-targets
echo 'Production enabled at https://rafael.ink. Record current.json, verify real browser analytics and fresh production logs; external-WAN availability and alert delivery remain separate checks.'
