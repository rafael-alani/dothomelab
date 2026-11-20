#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 && -d /etc/pve ]] || { echo 'Run on PVE as root' >&2; exit 1; }
repo="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
commit="$(git -C "$repo" rev-parse HEAD)"
target="/opt/dothomelab-branchline-routes/$commit"
archive="$(mktemp /var/tmp/branchline-routes.XXXXXX.tar)"
trap 'rm -f -- "$archive"' EXIT
git -C "$repo" archive HEAD hosts/staging/configure-routes.py hosts/staging/lifecycle.py \
  hosts/staging/ensure-certificate.mjs hosts/staging/reconcile-routes.mjs \
  hosts/staging/branchline/routes.json > "$archive"
pct exec 110 -- install -d -m 0755 "$target"
pct push 110 "$archive" /run/branchline-routes.tar --perms 0600
pct exec 110 -- tar -xf /run/branchline-routes.tar -C "$target"
pct exec 110 -- python3 -c '
import datetime, pathlib, sqlite3
root=pathlib.Path("/srv/appdata/docker/infra-nginx-proxy-manager")
backup=root/("database.sqlite.pre-branchline-"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S"))
with sqlite3.connect(root/"data/database.sqlite") as source, sqlite3.connect(backup) as target:
 source.backup(target)
 assert target.execute("PRAGMA integrity_check").fetchone()==("ok",)
backup.chmod(0o600)
print("Verified focused NPM rollback copy")'
pct exec 110 -- python3 "$target/hosts/staging/configure-routes.py" \
  --apps "$target/hosts/staging/branchline/routes.json"
pct exec 110 -- sh -c 'printf "%s\n" "$1" > "$2/DEPLOYED_COMMIT"' sh "$commit" "$target"
echo "Installed private Branchline routes from $commit; shared CT110 archive unchanged"
