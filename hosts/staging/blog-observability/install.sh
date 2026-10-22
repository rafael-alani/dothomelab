#!/usr/bin/env bash
# Run from a committed PVE checkout. Retain every prior source/data generation.
set -Eeuo pipefail
repo="$(git rev-parse --show-toplevel)"
commit="$(git rev-parse HEAD)"
[[ $EUID == 0 ]] && command -v pct >/dev/null || { echo 'Run on PVE as root' >&2; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo 'Use a clean committed checkout' >&2; exit 1; }
expected="${EXPECTED_STAGING_COMMIT:-c86e422e80cb1461c0127737927479dd4e1b931f}"
current="$(pct exec 114 -- cat /opt/dothomelab/DEPLOYED_COMMIT)"
[[ "$current" == "$expected" || "$current" == "$commit" ]] || {
  echo 'CT114 source changed; reconcile the candidate with the live revision first' >&2; exit 1;
}
python3 "$repo/hosts/staging/blog-observability/initialize.py"
archive="$(mktemp /tmp/blog-observability.XXXXXX.tar)"
trap 'rm -f -- "$archive"' EXIT
git archive HEAD >"$archive"
release="/opt/dothomelab-blog-observability/releases/$commit"
for guest in 110 112 114; do
  if ! pct exec "$guest" -- test -d "$release"; then
    pct exec "$guest" -- install -d -m 0755 "$release"
    pct push "$guest" "$archive" /run/blog-observability-source.tar --perms 0600
    pct exec "$guest" -- tar -xf /run/blog-observability-source.tar -C "$release"
    pct exec "$guest" -- rm -f /run/blog-observability-source.tar
    pct exec "$guest" -- sh -c 'printf "%s\n" "$1" >"$2/DEPLOYED_COMMIT"' sh "$commit" "$release"
  fi
done
here="$release/hosts/staging/blog-observability"
pct exec 114 -- bash "$here/deploy.sh"
# Retain a fresh consistent proxy rollback before adding only these two routes.
pct exec 110 -- python3 -c '
import sqlite3,sys
from pathlib import Path
source=Path("/srv/appdata/docker/infra-nginx-proxy-manager/data/database.sqlite")
target=source.parent.parent / ("database.sqlite.pre-blog-observability-" + sys.argv[1])
if not target.exists():
    with sqlite3.connect(source) as a, sqlite3.connect(target) as b:
        a.backup(b)
        assert b.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    target.chmod(0o600)
print("Proxy rollback integrity verified")
' "$commit"
pct exec 110 -- python3 "$release/hosts/staging/configure-routes.py" --apps "$here/routes.json"
pct exec 112 -- bash "$here/install-prometheus.sh"
# Install the complete CT114 source from its observed base, under the poller's
# existing lock. The previous archive is retained and no other app is deployed.
if [[ "$current" != "$commit" ]]; then
  pct exec 114 -- flock -w 60 /srv/appdata/docker/staging/deploy.lock \
    sh -eu -c '
      test "$(cat /opt/dothomelab/DEPLOYED_COMMIT)" = "$1"
      test ! -e "/opt/dothomelab.before-blog-observability-$2"
      cp -a "$3" "/opt/dothomelab.next-$2"
      mv /opt/dothomelab "/opt/dothomelab.before-blog-observability-$2"
      mv "/opt/dothomelab.next-$2" /opt/dothomelab
    ' sh "$current" "$commit" "$release"
fi
install -m 0755 "$repo/backup/pbs/blog-umami-database-backup.sh" \
  /etc/dothomelab/backup-pre.d/70-blog-umami-database
python3 "$repo/hosts/staging/include-in-backup.py"
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --app blog
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --app blog --verify
echo "Installed blog observability source $commit; browser/database/log verification remains required"
