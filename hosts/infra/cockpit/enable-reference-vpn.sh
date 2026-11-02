#!/usr/bin/env bash
# Infra only: extend read-only Media access to the inspected Mac's tailnet IP.
set -euo pipefail
[[ $EUID == 0 && $(hostname -s) == infra ]] || { echo 'Run inside Infra through pct exec.' >&2; exit 1; }
[[ $(net conf getparm Media 'read only') == [Yy]es ]] || exit 1
[[ $(net conf getparm Media path) == /vault/shared/media ]] || exit 1
[[ $(net conf getparm Vault path) == /vault/shared ]] || exit 1
before=$(net conf getparm global 'hosts allow')
[[ $before == '127.0.0.1 192.168.0.0/24' || $before == '127.0.0.1 192.168.0.0/24 100.65.199.88' ]] || {
  echo 'Unexpected access policy; inspect before extending it.' >&2; exit 1;
}
backup=/srv/appdata/docker/infra-samba/reference-vpn-rollback/$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 0700 "$backup"
net conf list > "$backup/registry.conf"
chmod 0600 "$backup/registry.conf"
# Restore and reload the preceding registry if any validation/action fails.
rollback() { net conf import "$backup/registry.conf" >/dev/null; smbcontrol all reload-config; }
trap rollback ERR
# Keep the writable administration share LAN-only before widening global access.
net conf setparm Vault 'hosts allow' '127.0.0.1 192.168.0.0/24'
net conf setparm Vault 'hosts deny' '0.0.0.0/0'
net conf setparm Media 'hosts allow' '127.0.0.1 192.168.0.0/24 100.65.199.88'
net conf setparm Media 'hosts deny' '0.0.0.0/0'
net conf setparm global 'hosts allow' '127.0.0.1 192.168.0.0/24 100.65.199.88'
testparm -s >/dev/null
smbcontrol all reload-config
trap - ERR
printf 'Read-only Media VPN allowance installed; rollback registry: %s/registry.conf\n' "$backup"
