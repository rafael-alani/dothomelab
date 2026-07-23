#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <LXC VMID> <compose path relative to repository>" >&2
  exit 2
fi

guest_vmid="$1"
compose_path="$2"
guest_env="/run/dothomelab.env"
host_env="/root/.env"

if [[ ! -r "$host_env" ]]; then
  echo "Missing production environment: $host_env" >&2
  exit 1
fi

if ! pct exec "$guest_vmid" -- test -r "/opt/dothomelab/$compose_path"; then
  echo "Sync the repository into LXC $guest_vmid first" >&2
  exit 1
fi

pct push "$guest_vmid" "$host_env" "$guest_env" --perms 0600
trap 'pct exec "$guest_vmid" -- rm -f "$guest_env" >/dev/null 2>&1 || true' EXIT

pct exec "$guest_vmid" -- docker compose \
  --env-file "$guest_env" \
  -f "/opt/dothomelab/$compose_path" \
  config --quiet

pct exec "$guest_vmid" -- docker compose \
  --env-file "$guest_env" \
  -f "/opt/dothomelab/$compose_path" \
  up -d

echo "Deployed $compose_path to LXC $guest_vmid"
