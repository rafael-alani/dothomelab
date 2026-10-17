#!/usr/bin/env bash
set -Eeuo pipefail
readonly here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly repo="$(cd -- "$here/../.." && pwd)"
[[ $EUID -eq 0 && -d /etc/pve ]] || { echo 'Run on PVE as root' >&2; exit 1; }
readonly revision="$(git -C "$repo" rev-parse HEAD)"
readonly destination=/usr/local/lib/dothomelab-staging-homarr
git -C "$repo" diff --exit-code HEAD -- hosts/staging/sync-homarr.py hosts/staging/lifecycle.py \
  hosts/staging/install-homarr-sync.sh hosts/staging/dothomelab-staging-homarr.service \
  hosts/staging/dothomelab-staging-homarr.timer >/dev/null
install -d -m 0755 "$destination/releases/$revision"
if [[ -f "$destination/releases/$revision/sync-homarr.py" ]]; then
  cmp "$here/sync-homarr.py" "$destination/releases/$revision/sync-homarr.py"
else
  install -m 0755 "$here/sync-homarr.py" "$destination/releases/$revision/"
fi
install -m 0644 "$here/lifecycle.py" "$destination/releases/$revision/lifecycle.py"
printf '%s\n' "$revision" >"$destination/releases/$revision/DEPLOYED_COMMIT"
ln -sfn "releases/$revision" "$destination/current.next"
mv -Tf "$destination/current.next" "$destination/current"
install -m 0644 "$here/dothomelab-staging-homarr.service" /etc/systemd/system/
install -m 0644 "$here/dothomelab-staging-homarr.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dothomelab-staging-homarr.timer
# Failure is visible in the service journal; it must not roll back a healthy app.
systemctl start dothomelab-staging-homarr.service
