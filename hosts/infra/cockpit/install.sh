#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify the guest OS" >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "debian" || "${VERSION_CODENAME:-}" != "bookworm" ]]; then
  echo "This installer expects Debian 12 (bookworm)" >&2
  exit 1
fi

install -m 0644 /dev/stdin /etc/apt/sources.list.d/bookworm-backports.list <<'EOF'
deb http://deb.debian.org/debian bookworm-backports main
EOF

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y -t bookworm-backports \
  cockpit \
  cockpit-system

DEBIAN_FRONTEND=noninteractive apt-get install -y \
  acl \
  attr \
  avahi-daemon \
  avahi-utils \
  curl \
  samba \
  samba-vfs-modules \
  smbclient \
  wsdd

readonly cockpit_files_url="https://deb.debian.org/debian/pool/main/c/cockpit-files/cockpit-files_36-1~bpo13+1_all.deb"
readonly cockpit_files_sha256="3255a9f3352a2f9ff0b957533dba1c3af99254efbb6659bf76489582b4932822"
readonly cockpit_file_sharing_url="https://github.com/45Drives/cockpit-file-sharing/releases/download/v4.6.1/cockpit-file-sharing_4.6.1-1bookworm_all.deb"
readonly cockpit_file_sharing_sha256="59da224a06cf4a77f4c52b48c8040408462d5c689ab5faa83530a6db973e2eab"

package_dir="$(mktemp -d)"
trap 'rm -rf -- "$package_dir"' EXIT

download_verified_package() {
  local url="$1"
  local sha256="$2"
  local target="$3"

  curl --fail --location --silent --show-error "$url" --output "$target"
  printf '%s  %s\n' "$sha256" "$target" | sha256sum --check --status
}

download_verified_package \
  "$cockpit_files_url" \
  "$cockpit_files_sha256" \
  "$package_dir/cockpit-files.deb"
download_verified_package \
  "$cockpit_file_sharing_url" \
  "$cockpit_file_sharing_sha256" \
  "$package_dir/cockpit-file-sharing.deb"

DEBIAN_FRONTEND=noninteractive apt-get install -y \
  "$package_dir/cockpit-files.deb" \
  "$package_dir/cockpit-file-sharing.deb"

backup_dir="/var/backups/dothomelab-samba/$(date --utc +%Y%m%dT%H%M%SZ)"
install -d -m 0700 "$backup_dir"
for config_file in \
  /etc/avahi/avahi-daemon.conf \
  /etc/hosts \
  /etc/samba/smb.conf \
  /etc/default/wsdd; do
  if [[ -f "$config_file" ]]; then
    install -m 0600 "$config_file" "$backup_dir/$(basename "$config_file")"
  fi
done
if net conf list >"$backup_dir/registry.conf" 2>/dev/null; then
  chmod 0600 "$backup_dir/registry.conf"
fi

current_hostname="$(hostname)"
if ! getent hosts "$current_hostname" >/dev/null; then
  printf '127.0.1.1\t%s\n' "$current_hostname" >>/etc/hosts
fi

install -m 0644 \
  "$script_dir/dothomelab-pihole-ip.service" \
  /etc/systemd/system/dothomelab-pihole-ip.service

install -m 0644 /dev/stdin /etc/samba/smb.conf <<'EOF'
[global]
	include = registry
EOF

net conf import --test "$script_dir/samba-registry.conf" >/dev/null
net conf import "$script_dir/samba-registry.conf"
testparm --suppress-prompt -s >/dev/null

install -m 0644 \
  "$script_dir/avahi-daemon.conf" \
  /etc/avahi/avahi-daemon.conf
install -m 0644 \
  "$script_dir/avahi-smb.service" \
  /etc/avahi/services/smb.service
install -m 0644 \
  "$script_dir/wsdd.default" \
  /etc/default/wsdd

systemctl daemon-reload
systemctl enable --now cockpit.socket
systemctl disable --now nmbd.service
systemctl disable --now nfs-server.service 2>/dev/null || true
systemctl disable --now nfs-kernel-server.service 2>/dev/null || true
systemctl disable --now nfs-client.target 2>/dev/null || true
systemctl disable --now nfs-blkmap.service 2>/dev/null || true
systemctl disable --now rpcbind.socket rpcbind.service 2>/dev/null || true
systemctl stop rpc-statd.service 2>/dev/null || true
systemctl enable --now smbd.service
systemctl enable --now avahi-daemon.service
systemctl enable --now wsdd.service
systemctl restart smbd.service avahi-daemon.service wsdd.service

echo "Cockpit Files and File Sharing are installed, and SMB is active."
echo "Run 'smbpasswd -a afa' interactively before connecting a client."
echo "Enable dothomelab-pihole-ip.service only at DNS cutover."
