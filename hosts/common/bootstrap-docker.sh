#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || {
  echo "Run as root inside the LXC." >&2
  exit 1
}

# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "debian" && "${VERSION_CODENAME:-}" == "bookworm" ]] || {
  echo "Docker application guests require Debian 12 (bookworm)." >&2
  exit 1
}

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git gnupg python3

install -d -m 0755 /etc/apt/keyrings
curl --fail --location --silent --show-error \
  https://download.docker.com/linux/debian/gpg \
  --output /etc/apt/keyrings/docker.asc
chmod 0644 /etc/apt/keyrings/docker.asc

install -m 0644 /dev/stdin /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y \
  containerd.io \
  docker-buildx-plugin \
  docker-ce \
  docker-ce-cli \
  docker-compose-plugin

install -d -m 0755 /etc/systemd/journald.conf.d
install -m 0644 /dev/stdin \
  /etc/systemd/journald.conf.d/20-dothomelab-size.conf <<'EOF'
[Journal]
SystemMaxUse=100M
EOF

systemctl enable --now docker
systemctl restart systemd-journald
docker info >/dev/null
docker compose version

install -d -m 0755 /etc/dothomelab
printf 'debian=%s\ndocker=%s\n' \
  "$VERSION_ID" "$(docker version --format '{{.Server.Version}}')" \
  >/etc/dothomelab/guest-provisioned

echo "Docker guest base is ready."
