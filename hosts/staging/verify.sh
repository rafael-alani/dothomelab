#!/usr/bin/env bash
set -Eeuo pipefail
readonly here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly repo="$(cd -- "$here/../.." && pwd)"
source "$repo/provision/inventory.env"
[[ $EUID -eq 0 ]] || { echo 'Run on PVE as root' >&2; exit 1; }
config="$(pct config 114)"
for expected in 'hostname: staging' 'unprivileged: 1' 'features: nesting=1' \
  "cores: ${CT_CORES[114]}" "memory: ${CT_MEMORY[114]}" \
  "mp0: $STAGING_APPDATA_HOST_PATH,mp=$STAGING_APPDATA_GUEST_PATH"; do
  grep -Fqx "$expected" <<<"$config"
done
! grep -qE '^(mp[1-9][0-9]*|dev[0-9]+):' <<<"$config"
grep -Fq "ip=${CT_IP[114]}/$LAN_PREFIX" <<<"$config"
grep -Fq "hwaddr=${CT_MAC[114]}" <<<"$config"
grep -qx 'onboot: 1' <<<"$config"
pct exec 114 -- mountpoint -q "$STAGING_APPDATA_GUEST_PATH"
pct exec 114 -- /opt/dothomelab/hosts/staging/deploy.py --verify
pct exec 114 -- systemctl is-enabled --quiet dothomelab-staging.timer
pct exec 114 -- systemctl is-active --quiet dothomelab-staging.timer
! pct exec 114 -- ss -ltn | grep -qE ':237[56][[:space:]]'
grep -E '^QUIESCE_CTIDS="[0-9 ]*114([ "]|$)' /etc/dothomelab/pbs-appdata.conf >/dev/null
[[ "$(pct exec 114 -- cat /opt/dothomelab/DEPLOYED_COMMIT)" == "$(git -C "$repo" rev-parse HEAD)" ]]
while read -r domain port; do
  pct exec 114 -- getent ahostsv4 "$domain" | grep -q '^192.168.0.110 '
  curl --fail --silent --show-error --resolve "$domain:443:192.168.0.110" \
    "https://$domain/api/health" | python3 -c 'import json,sys; assert json.load(sys.stdin)["ok"]'
done < <(python3 -c 'import json,sys; [print(a["hostname"],a["port"]) for a in json.load(open(sys.argv[1])).values()]' "$here/apps.json")
echo 'Staging identity, isolation, commit, data, polling, DNS and trusted HTTPS verified'
