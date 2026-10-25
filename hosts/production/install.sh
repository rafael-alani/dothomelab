#!/usr/bin/env bash
# PVE: install infrastructure and dormant publication helpers from committed Git.
set -Eeuo pipefail
repo="$(git rev-parse --show-toplevel)"
commit="$(git rev-parse HEAD)"
[[ $EUID == 0 && -d /etc/pve ]] || { echo 'Run on PVE as root'; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo 'Commit the scaffold before installation'; exit 1; }
"$repo/bootstrap.sh" --prod-only
archive="$(mktemp /run/production-source.XXXXXX.tar)"
trap 'rm -f -- "$archive"' EXIT
git archive HEAD >"$archive"
release="/opt/dothomelab-production/releases/$commit"
for guest in 110 112 114; do
  if ! pct exec "$guest" -- test -d "$release"; then
    pct exec "$guest" -- install -d -m 0755 "$release"
    pct push "$guest" "$archive" /run/production-source.tar --perms 0600
    pct exec "$guest" -- tar -xf /run/production-source.tar -C "$release"
    pct exec "$guest" -- rm -f /run/production-source.tar
    pct exec "$guest" -- sh -c 'printf "%s\n" "$1" >"$2/DEPLOYED_COMMIT"' sh "$commit" "$release"
  fi
  pct exec "$guest" -- ln -sfn "$release" /opt/dothomelab-production/current
done
python3 "$repo/hosts/staging/initialize-repo-key.py" --app blog --environment production
python3 "$repo/hosts/production/prepare-content.py"
pct exec 110 -- python3 "$release/hosts/production/configure-route.py"
pct exec 112 -- bash "$release/hosts/production/observability/install-prometheus.sh"
# Fix obsolete text assertions without replacing staging applications or Alloy.
pct exec 114 -- env BLOG_SOURCE_ROOT="$release" BLOG_OBSERVABILITY_COMMIT="$commit" \
  bash "$release/hosts/production/observability/update-staging-probes.sh"
echo "Scaffold installed at $commit. Register the dedicated read-only GitHub key; origin/main must exist before activation."
