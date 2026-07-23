#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <systemd drop-in path>" >&2
  exit 2
fi

[[ $EUID -eq 0 ]] || {
  echo "Run as root." >&2
  exit 1
}

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly daemon_source="$script_dir/daemon.json"
readonly dropin_source="$1"
readonly daemon_target="/etc/docker/daemon.json"
readonly dropin_dir="/etc/systemd/system/docker.service.d"
readonly dropin_target="$dropin_dir/20-dothomelab-remote-api.conf"
readonly tls_dir="/etc/docker/tls"

for path in "$daemon_source" "$dropin_source" \
  "$tls_dir/ca.pem" "$tls_dir/server-cert.pem" "$tls_dir/server-key.pem"; do
  [[ -s "$path" ]] || {
    echo "Missing required file: $path" >&2
    exit 1
  }
done

if [[ -e "$daemon_target" ]] && ! cmp -s "$daemon_source" "$daemon_target"; then
  echo "$daemon_target already contains unmanaged settings; merge live-restore manually." >&2
  exit 1
fi

install -d -m 0755 /etc/docker "$dropin_dir"
install -m 0644 "$daemon_source" "$daemon_target"
dockerd --validate --config-file "$daemon_target"

# Docker documents live-restore as reloadable. Enable and verify it before
# restarting dockerd with the additional TLS listener.
systemctl reload docker
for _ in {1..20}; do
  if [[ "$(docker info --format '{{.LiveRestoreEnabled}}')" == "true" ]]; then
    break
  fi
  sleep 1
done
[[ "$(docker info --format '{{.LiveRestoreEnabled}}')" == "true" ]] || {
  echo "Docker did not enable live-restore." >&2
  exit 1
}

install -m 0644 "$dropin_source" "$dropin_target"
systemctl daemon-reload

rollback_listener() {
  local exit_code=$?
  trap - ERR
  echo "Docker API deployment failed; removing the new listener." >&2
  rm -f "$dropin_target"
  systemctl daemon-reload
  systemctl restart docker
  exit "$exit_code"
}
trap rollback_listener ERR

systemctl restart docker
systemctl is-active --quiet docker
docker info >/dev/null
ss -lnt | grep -qE 'LISTEN.+:2376[[:space:]]'
trap - ERR

echo "Docker remote API enabled with mutual TLS; live-restore remains enabled."
