#!/usr/bin/env bash
set -Eeuo pipefail

readonly here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly network="servarr-hello_default"
readonly config="/docker/qbittorrent/qBittorrent/qBittorrent.conf"

[[ -s "$config" ]] || {
  echo "qBittorrent configuration is missing: $config" >&2
  exit 1
}

subnet="$(
  docker network inspect "$network" \
    --format '{{(index .IPAM.Config 0).Subnet}}'
)"
python3 - "$subnet" <<'PY'
import ipaddress
import sys
network = ipaddress.ip_network(sys.argv[1], strict=True)
if network.version != 4 or not network.is_private or network.prefixlen < 16:
    raise SystemExit(f"refusing unsafe qBittorrent bypass subnet: {network}")
PY

if python3 "$here/qbittorrent-access.py" --subnet "$subnet" --config "$config"; then
  echo "qBittorrent already trusts only the internal Compose subnet"
else
  docker stop --time 120 qbittorrent >/dev/null
  restart_pending=1
  restart_qbittorrent() {
    if [[ "$restart_pending" -eq 1 ]]; then
      docker start qbittorrent >/dev/null 2>&1 || true
    fi
  }
  trap restart_qbittorrent EXIT INT TERM

  python3 "$here/qbittorrent-access.py" --subnet "$subnet" --config "$config" --write

  docker start qbittorrent >/dev/null
  restart_pending=0
  trap - EXIT INT TERM
fi

deadline=$((SECONDS + 180))
while ((SECONDS < deadline)); do
  health="$(
    docker inspect --format '{{.State.Health.Status}}' qbittorrent 2>/dev/null ||
      true
  )"
  [[ "$health" == "healthy" ]] && break
  sleep 3
done
[[ "$health" == "healthy" ]] || {
  echo "qBittorrent did not become healthy after internal-access reconciliation" >&2
  exit 1
}

status="$(
  docker exec sonarr curl \
    --silent \
    --output /dev/null \
    --write-out '%{http_code}' \
    http://gluetun:8080/api/v2/app/version
)"
[[ "$status" == "200" ]] || {
  echo "qBittorrent rejected the internal Docker subnet with HTTP $status" >&2
  exit 1
}

echo "qBittorrent trusts the exact internal Compose subnet; localhost and LAN authentication remain enabled"
