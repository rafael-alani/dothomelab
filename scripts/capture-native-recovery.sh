#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPDATA_ROOT="/srv/appdata/docker"
readonly RECOVERY_DIR="$APPDATA_ROOT/recovery"
readonly INFRA_CTID=110
readonly PBS_CTID=113

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

[[ $EUID -eq 0 ]] || {
  echo "Run as root on the Proxmox host." >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$APPDATA_ROOT")" == "rpool/appdata/docker" ]] || {
  echo "$APPDATA_ROOT is not mounted from rpool/appdata/docker" >&2
  exit 1
}
for ctid in "$INFRA_CTID" "$PBS_CTID"; do
  pct status "$ctid" | grep -q "status: running" || {
    echo "LXC $ctid must be running" >&2
    exit 1
  }
done

install -d -o 100000 -g 100000 -m 0700 "$RECOVERY_DIR"

log "Briefly stopping Infra Tailscale and SMB for a consistent native-state copy"
services_stopped=true
restart_services() {
  if [[ "$services_stopped" == "true" ]]; then
    pct exec "$INFRA_CTID" -- systemctl start smbd.service tailscaled.service
  fi
}
trap restart_services EXIT INT TERM
pct exec "$INFRA_CTID" -- systemctl stop tailscaled.service smbd.service

pct exec "$INFRA_CTID" -- bash -euc '
  install -d -o 0 -g 0 -m 0700 \
    /srv/appdata/docker/tailscale \
    /srv/appdata/docker/infra-samba/private \
    /srv/appdata/docker/recovery
  if [[ -s /var/lib/tailscale/tailscaled.state ]]; then
    install -o 0 -g 0 -m 0600 \
      /var/lib/tailscale/tailscaled.state \
      /srv/appdata/docker/tailscale/tailscaled.state
  elif [[ -s /srv/appdata/docker/tailscale/tailscaled.state ]]; then
    chown 0:0 /srv/appdata/docker/tailscale/tailscaled.state
    chmod 0600 /srv/appdata/docker/tailscale/tailscaled.state
  else
    echo "No Tailscale state exists to capture" >&2
    exit 1
  fi

  samba_private="$(
    testparm -s --parameter-name="private dir" 2>/dev/null
  )"
  case "$samba_private" in
    /srv/appdata/docker/infra-samba/private)
      [[ -s "$samba_private/passdb.tdb" ]]
      ;;
    /var/lib/samba/private)
      cp -a /var/lib/samba/private/. \
        /srv/appdata/docker/infra-samba/private/
      ;;
    *)
      echo "Unexpected Samba private directory: $samba_private" >&2
      exit 1
      ;;
  esac
  getent shadow afa |
    cut -d: -f2 |
    install -o 0 -g 0 -m 0600 /dev/stdin \
      /srv/appdata/docker/recovery/infra-afa.shadow-hash
'

restart_services
services_stopped=false
trap - EXIT INT TERM

pbs_hash_temp="$(mktemp /tmp/dothomelab-pbs-root-hash.XXXXXX)"
trap 'rm -f -- "$pbs_hash_temp"' EXIT
pct exec "$PBS_CTID" -- getent shadow root |
  cut -d: -f2 >"$pbs_hash_temp"
[[ -s "$pbs_hash_temp" ]] || {
  echo "Could not capture the PBS root password hash" >&2
  exit 1
}
install -o 100000 -g 100000 -m 0600 \
  "$pbs_hash_temp" "$RECOVERY_DIR/pbs-root.shadow-hash"

[[ -s /etc/dothomelab/pbs-appdata.key ]] || {
  echo "Missing live PBS encryption key" >&2
  exit 1
}
install -o 100000 -g 100000 -m 0600 \
  /etc/dothomelab/pbs-appdata.key \
  "$RECOVERY_DIR/pbs-appdata.key"

pct exec "$INFRA_CTID" -- systemctl is-active --quiet \
  tailscaled.service smbd.service
for path in \
  "$APPDATA_ROOT/tailscale/tailscaled.state" \
  "$APPDATA_ROOT/infra-samba/private/passdb.tdb" \
  "$RECOVERY_DIR/infra-afa.shadow-hash" \
  "$RECOVERY_DIR/pbs-root.shadow-hash" \
  "$RECOVERY_DIR/pbs-appdata.key"; do
  [[ -s "$path" ]] || {
    echo "Native recovery capture is incomplete: $path" >&2
    exit 1
  }
  [[ "$(stat -c '%u:%g:%a' "$path")" == "100000:100000:600" ]] || {
    echo "Native recovery file has unsafe ownership or mode: $path" >&2
    exit 1
  }
done
cmp --silent \
  "$pbs_hash_temp" \
  "$RECOVERY_DIR/pbs-root.shadow-hash"
cmp --silent \
  /etc/dothomelab/pbs-appdata.key \
  "$RECOVERY_DIR/pbs-appdata.key"

log "Native Infra credentials/Tailscale state and the PBS recovery key are now in appdata"
