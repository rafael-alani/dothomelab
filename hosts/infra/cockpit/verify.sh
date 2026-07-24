#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

[[ $EUID -eq 0 ]] || fail "verification must run as root"
[[ "$(findmnt -n -o SOURCE -T /vault/shared)" == "vault/shared" ]] ||
  fail "/vault/shared is not mounted from vault/shared"
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker)" == "rpool/appdata/docker" ]] ||
  fail "/srv/appdata/docker is not mounted from rpool/appdata/docker"

[[ -r /usr/share/cockpit/files/manifest.json ]] ||
  fail "Cockpit Files is not installed"
find /usr/share/cockpit /usr/local/share/cockpit \
  -path '*/file-sharing/manifest.json' -print -quit 2>/dev/null |
  grep -q . || fail "Cockpit File Sharing is not installed"

systemctl is-active --quiet cockpit.socket ||
  fail "cockpit.socket is not active"
systemctl is-active --quiet smbd.service ||
  fail "smbd.service is not active"
systemctl is-active --quiet avahi-daemon.service ||
  fail "avahi-daemon.service is not active"
systemctl is-active --quiet wsdd.service ||
  fail "wsdd.service is not active"
systemctl is-active --quiet nmbd.service &&
  fail "legacy NetBIOS nmbd.service must remain inactive"
systemctl is-active --quiet nfs-server.service &&
  fail "NFS was installed only as a Cockpit File Sharing dependency and must remain inactive"
for unit in \
  nfs-client.target \
  rpcbind.service \
  rpcbind.socket \
  rpc-statd.service; do
  systemctl is-active --quiet "$unit" &&
    fail "$unit is not needed for the SMB-only deployment and must remain inactive"
done

getent hosts "$(hostname)" >/dev/null ||
  fail "the live hostname is not resolvable through /etc/hosts"
grep -Eq '^WSDD_PARAMS="[^"]*-i 192\.168\.0\.110([ "].*)?"$' /etc/default/wsdd ||
  fail "WSD discovery is not restricted to CT110's LAN address"
grep -Eq '^allow-interfaces=eth0$' /etc/avahi/avahi-daemon.conf ||
  fail "mDNS discovery is not restricted to eth0"

testparm --suppress-prompt -s >/dev/null ||
  fail "Samba configuration is invalid"
[[ "$(net conf getparm shared path)" == "/vault/shared" ]] ||
  fail "the shared Samba path is not /vault/shared"
[[ "$(net conf getparm shared 'valid users')" == "afa" ]] ||
  fail "the shared Samba share is not restricted to afa"
net conf getparm shared 'vfs objects' | grep -qw fruit ||
  fail "the macOS fruit VFS module is not enabled"
[[ "$(net conf getparm shared 'veto files')" == "/.ssh/.gnupg/.env/compose/" ]] ||
  fail "sensitive restore and legacy Compose directories are not hidden from SMB"

sudo -u afa test -r /vault/shared ||
  fail "afa cannot read /vault/shared"
sudo -u afa test -w /vault/shared ||
  fail "afa cannot write /vault/shared"
sudo -u afa test -r /srv/appdata/docker ||
  fail "afa cannot read the appdata root"

ss -lnt | awk '$4 ~ /:445$/ { found=1 } END { exit !found }' ||
  fail "SMB is not listening on TCP 445"
ss -lnt | grep -q '192\.168\.0\.110:445' ||
  fail "SMB is not listening on CT110's LAN address"

if ! pdbedit -L | cut -d: -f1 | grep -qx afa; then
  fail "Samba user afa is absent; run 'smbpasswd -a afa' interactively"
fi

printf 'OK Cockpit Files can browse both mounts; SMB shared is authenticated and macOS-optimized\n'
