#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || {
  echo "Run as root inside Infra." >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker)" == "rpool/appdata/docker" ]] || {
  echo "/srv/appdata/docker is not mounted from rpool/appdata/docker" >&2
  exit 1
}
[[ -c /dev/net/tun ]] || {
  echo "/dev/net/tun is not available" >&2
  exit 1
}

# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "debian" && "${VERSION_CODENAME:-}" == "bookworm" ]] || {
  echo "Tailscale provisioning expects Debian 12 (bookworm)." >&2
  exit 1
}

state_dir="/srv/appdata/docker/tailscale"
state_file="$state_dir/tailscaled.state"
legacy_state="/var/lib/tailscale/tailscaled.state"

install -d -m 0700 "$state_dir"
install -d -m 0755 /usr/share/keyrings
curl --fail --location --silent --show-error \
  "https://pkgs.tailscale.com/stable/debian/${VERSION_CODENAME}.noarmor.gpg" \
  --output /usr/share/keyrings/tailscale-archive-keyring.gpg
curl --fail --location --silent --show-error \
  "https://pkgs.tailscale.com/stable/debian/${VERSION_CODENAME}.tailscale-keyring.list" \
  --output /etc/apt/sources.list.d/tailscale.list

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y tailscale

if [[ ! -s "$state_file" && -s "$legacy_state" ]]; then
  systemctl stop tailscaled.service
  install -m 0600 "$legacy_state" "$state_file"
fi

install -d -m 0755 /etc/systemd/system/tailscaled.service.d
install -m 0644 /dev/stdin \
  /etc/systemd/system/tailscaled.service.d/20-dothomelab-state.conf <<EOF
[Service]
ExecStart=
ExecStart=/usr/sbin/tailscaled --state=$state_file --socket=/run/tailscale/tailscaled.sock --port=\${PORT} \$FLAGS
EOF
install -m 0644 /dev/stdin /etc/sysctl.d/99-dothomelab-tailscale.conf <<'EOF'
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF

sysctl --system >/dev/null
systemctl daemon-reload
systemctl enable --now tailscaled.service

tailscale_online() {
  tailscale status --json 2>/dev/null |
    python3 -c 'import json,sys; raise SystemExit(not bool(json.load(sys.stdin).get("Self", {}).get("Online")))' 2>/dev/null
}

for _ in {1..30}; do
  tailscale_online && break
  sleep 1
done

if ! tailscale_online; then
  : "${TAILSCALE_AUTH_KEY:?TAILSCALE_AUTH_KEY is required when no restored Tailscale state exists}"
  tailscale up \
    --auth-key="$TAILSCALE_AUTH_KEY" \
    --advertise-exit-node \
    --advertise-routes=192.168.0.0/24 \
    --accept-dns=true \
    --hostname=infra
fi

tailscale set \
  --advertise-exit-node \
  --advertise-routes=192.168.0.0/24 \
  --accept-dns=true

echo "Tailscale is installed with state on SSD appdata."
