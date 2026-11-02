#!/usr/bin/env bash
# PVE-only: install the restricted, non-Docker ingest endpoint.
set -euo pipefail
[[ $EUID == 0 && -x /usr/sbin/pct ]] || { echo 'Run on PVE as root.' >&2; exit 1; }
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
revision=${1:?Pass the committed deployment revision}
[[ $revision =~ ^[0-9a-f]{40}$ ]] || exit 2
state=/srv/appdata/docker/reference-media
archive=/vault/shared/media/references
[[ $(findmnt -n -o SOURCE -T /vault/shared) == vault/shared ]] || exit 1
[[ $(findmnt -n -o SOURCE -T /srv/appdata/docker) == rpool/appdata/docker ]] || exit 1
keyfile=${2:-$state/ingest.pub}
[[ -f $keyfile && ! -L $keyfile ]] || { echo 'Missing retained ingestion public key.' >&2; exit 1; }
[[ $(wc -l < "$keyfile") == 1 ]] && ssh-keygen -lf "$keyfile" >/dev/null
[[ $(cut -d ' ' -f1 "$keyfile") == ssh-ed25519 ]] || exit 1
if ! getent passwd reference-ingest >/dev/null; then
  useradd --system --create-home --home-dir /var/lib/reference-ingest --shell /bin/sh reference-ingest
fi
for folder in "$state" "$archive" "$archive/objects"; do
  [[ ! -L $folder ]] || { echo 'Refusing symlink.' >&2; exit 1; }
done
# Only these exact directories change owner. Existing immutable objects and
# every other media/appdata tree retain their ownership and permissions.
install -d -o reference-ingest -g reference-ingest -m 0700 "$state"
install -d -o reference-ingest -g reference-ingest -m 0755 "$archive" "$archive/objects"
if [[ $keyfile != "$state/ingest.pub" ]]; then install -o root -g root -m 0644 "$keyfile" "$state/ingest.pub"; fi
release=/usr/local/lib/dothomelab-reference-media/releases/$revision
install -d -o root -g root -m 0755 "$release"
install -o root -g root -m 0644 "$source_dir/archive.py" "$release/archive.py"
printf '%s\n' "$revision" > "$release/DEPLOYED_COMMIT"
install -d -o root -g root -m 0700 /var/lib/reference-ingest/.ssh
# Keep the exact preceding release and key file for reversible activation.
if [[ -f /var/lib/reference-ingest/.ssh/authorized_keys ]]; then
  cp -p /var/lib/reference-ingest/.ssh/authorized_keys "$state/authorized_keys.before-$(date -u +%Y%m%dT%H%M%SZ)"
fi
printf 'restrict,command="/usr/bin/python3 %s/archive.py" %s\n' "$release" "$(cat "$state/ingest.pub")" > /var/lib/reference-ingest/.ssh/authorized_keys
chmod 0600 /var/lib/reference-ingest/.ssh/authorized_keys
chown root:root /var/lib/reference-ingest/.ssh/authorized_keys
# sshd must traverse the root-owned directory as the account for key auth.
chmod 0755 /var/lib/reference-ingest/.ssh
printf '%s\n' "$revision" > "$state/DEPLOYED_COMMIT"
echo 'Restricted reference ingestion installed; no shell, forwarding, or delete operation.'
