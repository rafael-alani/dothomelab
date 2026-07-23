#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <LXC VMID>" >&2
  exit 2
fi

guest_vmid="$1"
repo_root="$(git rev-parse --show-toplevel)"
commit_sha="$(git -C "$repo_root" rev-parse HEAD)"
archive_path="$(mktemp /tmp/dothomelab-repo.XXXXXX.tar)"
trap 'rm -f "$archive_path"' EXIT

git -C "$repo_root" archive --format=tar HEAD >"$archive_path"

pct exec "$guest_vmid" -- install -d -m 0755 /opt/dothomelab
pct push "$guest_vmid" "$archive_path" /tmp/dothomelab-repo.tar --perms 0600
pct exec "$guest_vmid" -- tar -xf /tmp/dothomelab-repo.tar -C /opt/dothomelab
pct exec "$guest_vmid" -- rm -f /tmp/dothomelab-repo.tar
pct exec "$guest_vmid" -- sh -c \
  "printf '%s\n' '$commit_sha' >/opt/dothomelab/DEPLOYED_COMMIT"

echo "Synced commit $commit_sha to LXC $guest_vmid"
