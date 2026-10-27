#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <LXC VMID>" >&2
  exit 2
fi

guest_vmid="$1"
[[ "$guest_vmid" =~ ^[0-9]+$ ]] || { echo "Invalid LXC VMID" >&2; exit 2; }
exec 9>"/run/lock/dothomelab-repo-$guest_vmid.lock"
flock --nonblock 9 || { echo "Another guest repository deployment is running" >&2; exit 1; }
repo_root="$(git rev-parse --show-toplevel)"
commit_sha="$(git -C "$repo_root" rev-parse HEAD)"
if [[ "$guest_vmid" == 110 ]]; then
  python3 "$repo_root/hosts/infra/obsidian-sync/backup-runtime.py" check-repo "$repo_root"
fi
archive_path="$(mktemp /tmp/dothomelab-repo.XXXXXX.tar)"
trap 'rm -f "$archive_path"' EXIT

git -C "$repo_root" archive --format=tar HEAD >"$archive_path"

pct exec "$guest_vmid" -- rm -rf /opt/dothomelab.next
pct exec "$guest_vmid" -- install -d -m 0755 /opt/dothomelab.next
pct push "$guest_vmid" "$archive_path" /tmp/dothomelab-repo.tar --perms 0600
pct exec "$guest_vmid" -- tar -xf /tmp/dothomelab-repo.tar -C /opt/dothomelab.next
pct exec "$guest_vmid" -- rm -f /tmp/dothomelab-repo.tar
if [[ "$guest_vmid" == 110 ]]; then
  guard=/usr/local/lib/dothomelab-proton-backup/current/backup-runtime.py
  if ! pct exec 110 -- test -f "$guard"; then
    guard=/opt/dothomelab.next/hosts/infra/obsidian-sync/backup-runtime.py
  fi
  pct exec 110 -- python3 "$guard" check-repo /opt/dothomelab.next
fi
pct exec "$guest_vmid" -- sh -euc "
  printf '%s\n' '$commit_sha' >/opt/dothomelab.next/DEPLOYED_COMMIT
  if test -e /opt/dothomelab.previous; then
    mv /opt/dothomelab.previous /opt/dothomelab.previous.\$(date -u +%Y%m%dT%H%M%S).\$\$
  fi
  if test -d /opt/dothomelab; then
    mv /opt/dothomelab /opt/dothomelab.previous
  fi
  mv /opt/dothomelab.next /opt/dothomelab
"

echo "Synced commit $commit_sha to LXC $guest_vmid"
