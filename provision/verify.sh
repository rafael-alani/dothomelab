#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly repo_root="$(cd -- "$script_dir/.." && pwd)"
# shellcheck disable=SC1091
source "$script_dir/inventory.env"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

ok() {
  printf 'OK   %s\n' "$*"
}

[[ $EUID -eq 0 ]] || fail "run verification as root on Proxmox"
[[ -s /root/.env ]] || fail "production /root/.env is missing"

for command_name in pct proxmox-backup-client qm systemctl zfs zpool; do
  command -v "$command_name" >/dev/null ||
    fail "required command is missing: $command_name"
done

[[ "$(zpool status -x)" == "all pools are healthy" ]] ||
  fail "one or more ZFS pools are unhealthy"
[[ "$(zfs get -H -o value mountpoint "$APPDATA_DATASET")" == "$APPDATA_MOUNT" ]] ||
  fail "$APPDATA_DATASET mountpoint drifted"
[[ "$(zfs get -H -o value mountpoint "$SHARED_DATASET")" == "$SHARED_MOUNT" ]] ||
  fail "$SHARED_DATASET mountpoint drifted"
[[ "$(zfs get -H -o value mountpoint "$PBS_DATASET")" == "$PBS_MOUNT" ]] ||
  fail "$PBS_DATASET mountpoint drifted"
ok "ZFS pools and canonical datasets are healthy"

"$repo_root/provision/verify-media-contract.sh" --live
"$repo_root/hosts/haos/verify.sh"

expected_mounts=()
expected_mounts[102]="/vault/shared,mp=/data|/srv/appdata/docker,mp=/docker"
expected_mounts[110]="/srv/appdata/docker,mp=/srv/appdata/docker|/vault/shared,mp=/vault/shared"
expected_mounts[112]="/vault/shared,mp=/data,ro=1|/srv/appdata/docker,mp=/srv/appdata/docker|/vault/shared/media/yt-dlp,mp=/downloads|/vault/shared/media/music,mp=/music|/vault/shared/media/slskd,mp=/slskd-downloads|/vault/shared/media/podcasts,mp=/podcasts|/vault/shared/media/storyteller,mp=/storyteller"
expected_mounts[113]="/vault/pbs_datastore,mp=/mnt/datastore/appdata"
readonly -a expected_mounts

for ctid in "${ALL_CTIDS[@]}"; do
  pct status "$ctid" | grep -q "status: running" ||
    fail "LXC $ctid is not running"
  config="$(pct config "$ctid")"
  grep -qx "hostname: ${CT_HOSTNAME[$ctid]}" <<<"$config" ||
    fail "LXC $ctid hostname drifted"
  grep -qx "unprivileged: 1" <<<"$config" ||
    fail "LXC $ctid is not unprivileged"
  for expected in \
    "cores: ${CT_CORES[$ctid]}" \
    "memory: ${CT_MEMORY[$ctid]}" \
    "swap: ${CT_SWAP[$ctid]}"; do
    grep -qx "$expected" <<<"$config" ||
      fail "LXC $ctid does not match declared setting $expected"
  done
  grep -qE \
    "^rootfs: ${PVE_ROOTFS_STORAGE}:.*[,]size=${CT_ROOTFS_GB[$ctid]}G(,|$)" \
    <<<"$config" ||
    fail "LXC $ctid root disk storage or size drifted"
  grep -qE \
    "^net0: .*bridge=${PVE_BRIDGE}.*hwaddr=${CT_MAC[$ctid]}([,]|$)" \
    <<<"$config" ||
    fail "LXC $ctid bridge or MAC address drifted"
  grep -qE "ip=(${CT_IP[$ctid]}/${LAN_PREFIX}|dhcp)(,|$)" <<<"$config" ||
    fail "LXC $ctid has an unexpected IPv4 definition"
  IFS='|' read -r -a mounts <<<"${expected_mounts[$ctid]}"
  for mount in "${mounts[@]}"; do
    grep -Fq "$mount" <<<"$config" ||
      fail "LXC $ctid is missing mount definition $mount"
  done
  ok "LXC $ctid ${CT_HOSTNAME[$ctid]} is running with declared mounts"
done

wait_for_docker_health() {
  local ctid="$1"
  local deadline=$((SECONDS + 600))
  local pending
  while ((SECONDS < deadline)); do
    pending="$(
      pct exec "$ctid" -- docker ps -q |
        xargs -r pct exec "$ctid" -- docker inspect \
          --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' |
        grep -Ec '^(starting|unhealthy)$' || true
    )"
    [[ "$pending" == "0" ]] && return 0
    sleep 5
  done
  fail "Docker health checks did not settle in LXC $ctid"
}

for ctid in "${APPLICATION_CTIDS[@]}"; do
  pct exec "$ctid" -- docker info >/dev/null ||
    fail "Docker is unavailable in LXC $ctid"
  wait_for_docker_health "$ctid"
  running_count="$(
    pct exec "$ctid" -- docker ps --format '{{.ID}}' |
      awk 'END {print NR}'
  )"
  [[ "$running_count" == "${CT_DOCKER_COUNT[$ctid]}" ]] ||
    fail "LXC $ctid has $running_count active containers; expected ${CT_DOCKER_COUNT[$ctid]}"
done
ok "Docker is running; all 66 declared containers are active and healthy"

check_projects() {
  local ctid="$1"
  shift
  local projects
  projects="$(pct exec "$ctid" -- docker compose ls --format json)"
  local expected
  for expected in "$@"; do
    grep -Fq "\"Name\":\"$expected\"" <<<"$projects" ||
      fail "Compose project $expected is missing in LXC $ctid"
  done
}

check_projects 102 servarr-hello shelfarr
check_projects 110 infra-services n8n obsidian-sync pulse wud
check_projects 112 \
  audiobookshelf \
  apps-mealie \
  apps-services \
  bar-assistant \
  bookorbit \
  droppedneedle \
  immichframe \
  immich-migration \
  kavita \
  loki \
  media \
  paperless-gpt \
  paperless-ngx \
  pinepods \
  prometheus \
  snapotter \
  slskd \
  storyteller \
  stirling-pdf \
  wizarr \
  yt-dlp-web-ui \
  zotero-webdav
ok "all 29 declared Compose projects are running"

pct exec 110 -- docker \
  --host "tcp://${CT_IP[102]}:2376" \
  --tlsverify \
  --tlscacert /etc/dothomelab/wud-docker-api/ca.pem \
  --tlscert /etc/dothomelab/wud-docker-api/client-cert.pem \
  --tlskey /etc/dothomelab/wud-docker-api/client-key.pem \
  info >/dev/null ||
  fail "Servarr Docker mTLS endpoint failed"
pct exec 110 -- docker \
  --host "tcp://${CT_IP[112]}:2376" \
  --tlsverify \
  --tlscacert /etc/dothomelab/wud-docker-api/ca.pem \
  --tlscert /etc/dothomelab/wud-docker-api/client-cert.pem \
  --tlskey /etc/dothomelab/wud-docker-api/client-key.pem \
  info >/dev/null ||
  fail "Apps Docker mTLS endpoint failed"
ok "central WUD can authenticate to both remote Docker APIs"

pct exec 102 -- /opt/dothomelab/hosts/servarr/hello/verify.sh
"$repo_root/scripts/initialize-shelfarr-audiobookshelf-env.py" \
  --env-file /root/.env \
  --check
"$repo_root/scripts/initialize-storyteller-env.py" \
  --env-file /root/.env \
  --check
"$repo_root/scripts/initialize-pinepods-env.py" \
  --env-file /root/.env \
  --check
pct exec 102 -- /opt/dothomelab/hosts/servarr/shelfarr/verify.sh
pct exec 110 -- /opt/dothomelab/hosts/infra/services/verify.sh
pct exec 110 -- /opt/dothomelab/hosts/infra/cockpit/verify.sh
pct exec 110 -- /opt/dothomelab/hosts/infra/obsidian-sync/verify.sh
pct exec 110 -- /opt/dothomelab/hosts/infra/n8n/verify.sh
pct exec 110 -- /opt/dothomelab/hosts/infra/pulse/verify.sh
"$repo_root/hosts/infra/pulse/configure-monitoring.py" --verify
systemctl cat dothomelab-proton-backup.service --no-pager >/dev/null ||
  fail "PVE Proton backup service is not installed"
systemctl cat dothomelab-proton-backup.timer --no-pager >/dev/null ||
  fail "PVE Proton backup timer is not installed"
if systemctl is-enabled --quiet dothomelab-proton-backup.timer; then
  ok "PVE fortnightly Proton backup due-check is enabled"
else
  printf 'pending - PVE Proton timer is disabled until authenticated restore verification\n'
fi
pct exec 110 -- tailscale status --json |
  python3 -c '
import json
import sys
state = json.load(sys.stdin)
if not state.get("Self", {}).get("Online"):
    raise SystemExit("Infra Tailscale node is offline")
'
pct exec 112 -- /opt/dothomelab/hosts/apps/immich/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/audiobookshelf/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/pinepods/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/bar-assistant/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/bookorbit/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/storyteller/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/slskd/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/droppedneedle/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/immichframe/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/kavita/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/loki/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/media/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/mealie/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/prometheus/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/services/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/snapotter/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/stirling-pdf/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/wizarr/verify.sh
pct exec 112 -- /opt/dothomelab/hosts/apps/yt-dlp-web-ui/verify.sh

pct push 110 /root/.env /run/dothomelab.env --perms 0600
pct exec 110 -- bash -lc \
  'trap "rm -f /run/dothomelab.env" EXIT
   source /opt/dothomelab/hosts/common/load-env.sh
   load_dothomelab_env /run/dothomelab.env
   /opt/dothomelab/hosts/infra/n8n/configure-owner.py --verify'

pct push 112 /root/.env /run/dothomelab.env --perms 0600
cleanup_guest_env() {
  pct exec 112 -- rm -f /run/dothomelab.env >/dev/null 2>&1 || true
}
trap cleanup_guest_env EXIT
pct exec 112 -- bash -lc \
  'source /opt/dothomelab/hosts/common/load-env.sh
   load_dothomelab_env /run/dothomelab.env
   /opt/dothomelab/hosts/apps/paperless-ngx/verify.sh
   /opt/dothomelab/hosts/apps/paperless-gpt/verify.sh
   exec /opt/dothomelab/hosts/apps/zotero-webdav/verify.sh'
cleanup_guest_env
trap - EXIT
ok "all focused application, native-service, and data verifiers passed"

pct exec 113 -- proxmox-backup-manager datastore show appdata >/dev/null ||
  fail "PBS appdata datastore is not configured"
prune_jobs="$(
  pct exec 113 -- proxmox-backup-manager prune-job list --output-format json
)"
python3 -c '
import json
import sys
jobs = [job for job in json.load(sys.stdin) if job.get("store") == "appdata"]
if len(jobs) != 1:
    raise SystemExit(f"expected one appdata prune job, found {len(jobs)}")
job = jobs[0]
expected = {
    "keep-last": 7,
    "keep-daily": 14,
    "keep-weekly": 8,
    "keep-monthly": 12,
    "schedule": "*-*-* 03:00",
}
drift = {key: (job.get(key), value) for key, value in expected.items()
         if job.get(key) != value}
if drift:
    raise SystemExit(f"appdata prune policy drift: {drift}")
' <<<"$prune_jobs" ||
  fail "PBS appdata prune policy is missing or drifted"
pct exec 113 -- proxmox-backup-manager verify-job show appdata-monthly-full >/dev/null ||
  fail "PBS monthly full-verification job is missing"
systemctl is-enabled --quiet dothomelab-appdata-backup.timer ||
  fail "PVE appdata backup timer is not enabled"
systemctl is-enabled --quiet dothomelab-appdata-backup.service ||
  fail "PVE appdata backup service is not installed"
[[ -x /etc/dothomelab/backup-pre.d/20-paperless-database ]] ||
  fail "Paperless logical database pre-backup hook is missing"
[[ -x /etc/dothomelab/backup-pre.d/30-snapotter-database ]] ||
  fail "SnapOtter logical database pre-backup hook is missing"
[[ -x /etc/dothomelab/backup-pre.d/40-bookorbit-database ]] ||
  fail "BookOrbit logical database pre-backup hook is missing"
[[ -x /etc/dothomelab/backup-pre.d/50-storyteller-database ]] ||
  fail "Storyteller SQLite pre-backup hook is missing"
[[ -x /etc/dothomelab/backup-pre.d/60-pinepods-database ]] ||
  fail "PinePods logical database pre-backup hook is missing"
[[ -x /usr/local/sbin/dothomelab-haos-backup ]] ||
  fail "HAOS VM backup command is missing"

# A successful authenticated list is useful even when a newly initialized
# datastore has not received its first scheduled backup yet.
# shellcheck disable=SC1091
source /etc/dothomelab/pbs-appdata.conf
export PBS_REPOSITORY PBS_FINGERPRINT PBS_PASSWORD_FILE
snapshot_json="$(proxmox-backup-client snapshot list --output-format json)"
snapshot_count="$(
  python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' \
    <<<"$snapshot_json"
)"
ok "PBS datastore authentication works; retained snapshots=$snapshot_count"

head_commit="$(git -C "$repo_root" rev-parse HEAD)"
for ctid in "${APPLICATION_CTIDS[@]}"; do
  deployed_commit="$(pct exec "$ctid" -- cat /opt/dothomelab/DEPLOYED_COMMIT)"
  [[ "$deployed_commit" == "$head_commit" ]] ||
    fail "LXC $ctid deploys $deployed_commit, expected $head_commit"
done
ok "all application guests deploy repository commit $head_commit"

printf '\nVerification passed.\n'
printf 'External contract: router DNS=%s; TCP %s -> %s. Router state was not mutated.\n' \
  "$ROUTER_DHCP_DNS" "$ROUTER_TCP_FORWARD_PORTS" "$ROUTER_TCP_FORWARD_TARGET"
