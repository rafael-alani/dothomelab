#!/usr/bin/env bash
set -Eeuo pipefail

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

if grep -Fqx "WebUI\\AuthSubnetWhitelist=$subnet" "$config" &&
  grep -Fqx 'WebUI\AuthSubnetWhitelistEnabled=true' "$config" &&
  grep -Fqx 'WebUI\LocalHostAuth=false' "$config"; then
  echo "qBittorrent already trusts only localhost and the internal Compose subnet"
else
  docker stop --time 120 qbittorrent >/dev/null
  restart_pending=1
  restart_qbittorrent() {
    if [[ "$restart_pending" -eq 1 ]]; then
      docker start qbittorrent >/dev/null 2>&1 || true
    fi
  }
  trap restart_qbittorrent EXIT INT TERM

  python3 - "$config" "$subnet" <<'PY'
from pathlib import Path
import os
import sys
import tempfile

path = Path(sys.argv[1])
subnet = sys.argv[2]
desired = {
    r"WebUI\AuthSubnetWhitelist": subnet,
    r"WebUI\AuthSubnetWhitelistEnabled": "true",
    r"WebUI\LocalHostAuth": "false",
}
lines = path.read_text(encoding="utf-8").splitlines()
found = set()
result = []
for line in lines:
    key = line.split("=", 1)[0]
    if key in desired:
        result.append(f"{key}={desired[key]}")
        found.add(key)
    else:
        result.append(line)
if found != set(desired):
    try:
        preferences = result.index("[Preferences]") + 1
    except ValueError as error:
        raise SystemExit("qBittorrent [Preferences] section is missing") from error
    for key in sorted(set(desired) - found):
        result.insert(preferences, f"{key}={desired[key]}")
        preferences += 1

stat = path.stat()
descriptor, temporary = tempfile.mkstemp(prefix=".qbit.", dir=path.parent)
try:
    os.fchmod(descriptor, stat.st_mode & 0o777)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("\n".join(result) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chown(temporary, stat.st_uid, stat.st_gid)
    os.replace(temporary, path)
finally:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
PY

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

forwarded_port="$(
  docker exec gluetun cat /tmp/gluetun/forwarded_port 2>/dev/null ||
    true
)"
[[ "$forwarded_port" =~ ^[0-9]+$ ]] &&
  ((forwarded_port >= 1024 && forwarded_port <= 65535)) || {
  echo "Gluetun has no valid ProtonVPN forwarded port" >&2
  exit 1
}

docker exec gluetun wget \
  -qO- \
  --post-data \
  "json={\"listen_port\":$forwarded_port,\"current_network_interface\":\"tun0\",\"random_port\":false,\"upnp\":false}" \
  http://127.0.0.1:8080/api/v2/app/setPreferences >/dev/null ||
  {
    echo "Gluetun could not apply the forwarded port to qBittorrent" >&2
    exit 1
  }

docker exec gluetun wget \
  -qO- \
  http://127.0.0.1:8080/api/v2/app/preferences |
  python3 -c '
import json
import sys

expected = int(sys.argv[1])
preferences = json.load(sys.stdin)
if preferences.get("listen_port") != expected:
    raise SystemExit("qBittorrent does not use the ProtonVPN forwarded port")
if preferences.get("current_network_interface") != "tun0":
    raise SystemExit("qBittorrent is not bound to the VPN interface")
if preferences.get("random_port") is not False:
    raise SystemExit("qBittorrent random port selection is enabled")
if preferences.get("upnp") is not False:
    raise SystemExit("qBittorrent UPnP is enabled behind Gluetun")
if preferences.get("bypass_local_auth") is not True:
    raise SystemExit("qBittorrent localhost authentication bypass is disabled")
' "$forwarded_port"

echo "qBittorrent trusts only localhost and the exact internal Compose subnet; ProtonVPN forwarded port applied; LAN authentication unchanged"
