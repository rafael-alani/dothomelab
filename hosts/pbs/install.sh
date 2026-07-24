#!/usr/bin/env bash
set -Eeuo pipefail

readonly env_file="${1:-/run/dothomelab.env}"
readonly token_output="${2:-}"
readonly datastore_path="/mnt/datastore/appdata"
readonly keyring="/usr/share/keyrings/proxmox-archive-keyring.gpg"
readonly keyring_sha256="136673be77aba35dcce385b28737689ad64fd785a797e57897589aed08db6e45"

[[ $EUID -eq 0 ]] || {
  echo "Run as root inside the PBS LXC." >&2
  exit 1
}
[[ -r "$env_file" ]] || {
  echo "Missing recovery environment: $env_file" >&2
  exit 1
}
[[ "$(findmnt -n -o SOURCE -T "$datastore_path")" == "vault/pbs_datastore" ]] || {
  echo "$datastore_path is not mounted from vault/pbs_datastore" >&2
  exit 1
}

# shellcheck disable=SC1091
source /opt/dothomelab/hosts/common/load-env.sh
load_dothomelab_env "$env_file"

if [[ -n "${PBS_ROOT_PASSWORD:-}" ]]; then
  [[ "$PBS_ROOT_PASSWORD" != *:* && "$PBS_ROOT_PASSWORD" != *$'\n'* ]] || {
    echo "PBS_ROOT_PASSWORD may not contain a colon or newline." >&2
    exit 1
  }
fi

# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "debian" && "${VERSION_CODENAME:-}" == "trixie" ]] || {
  echo "PBS requires Debian 13 (trixie)." >&2
  exit 1
}

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl jq
curl --fail --location --silent --show-error \
  https://enterprise.proxmox.com/debian/proxmox-archive-keyring-trixie.gpg \
  --output "$keyring"
printf '%s  %s\n' "$keyring_sha256" "$keyring" | sha256sum --check --status

install -m 0644 /dev/stdin /etc/apt/sources.list.d/proxmox.sources <<'EOF'
Types: deb
URIs: http://download.proxmox.com/debian/pbs
Suites: trixie
Components: pbs-no-subscription
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
EOF

apt-get update
apt-get install -y proxmox-backup-server
if [[ -n "${PBS_ROOT_PASSWORD:-}" ]]; then
  printf 'root:%s\n' "$PBS_ROOT_PASSWORD" | chpasswd
fi
systemctl enable --now proxmox-backup-proxy.service proxmox-backup.service

if proxmox-backup-manager datastore show appdata >/dev/null 2>&1; then
  proxmox-backup-manager datastore update appdata \
    --comment "Encrypted host appdata backups" \
    --gc-schedule "Sun *-*-* 04:00" \
    --verify-new true
else
  proxmox-backup-manager datastore create appdata "$datastore_path" \
    --comment "Encrypted host appdata backups" \
    --gc-schedule "Sun *-*-* 04:00" \
    --reuse-datastore true \
    --verify-new true
fi

prune_job_ids="$(
  proxmox-backup-manager prune-job list --output-format json |
    jq -r '.[] | select(.store == "appdata") | .id'
)"
prune_job_count="$(grep -c . <<<"$prune_job_ids" || true)"
if [[ "$prune_job_count" -gt 1 ]]; then
  echo "Multiple prune jobs target appdata; reconcile them before bootstrap" >&2
  exit 1
elif [[ "$prune_job_count" -eq 1 ]]; then
  prune_job_id="$prune_job_ids"
  proxmox-backup-manager prune-job update "$prune_job_id" \
    --schedule "*-*-* 03:00" \
    --store appdata \
    --keep-last 7 \
    --keep-daily 14 \
    --keep-weekly 8 \
    --keep-monthly 12
else
  proxmox-backup-manager prune-job create appdata-daily \
    --schedule "*-*-* 03:00" \
    --store appdata \
    --keep-last 7 \
    --keep-daily 14 \
    --keep-weekly 8 \
    --keep-monthly 12
fi

if proxmox-backup-manager verify-job show appdata-monthly-full >/dev/null 2>&1; then
  proxmox-backup-manager verify-job update appdata-monthly-full \
    --store appdata \
    --schedule "*-*-01 05:00" \
    --ignore-verified false \
    --comment "Reverify every appdata snapshot monthly"
else
  proxmox-backup-manager verify-job create appdata-monthly-full \
    --store appdata \
    --schedule "*-*-01 05:00" \
    --ignore-verified false \
    --comment "Reverify every appdata snapshot monthly"
fi

if ! proxmox-backup-manager user list --output-format json |
  jq -e '.[] | select(.userid == "backup@pbs")' >/dev/null; then
  proxmox-backup-manager user create backup@pbs \
    --comment "PVE host appdata backup client"
fi

if [[ -n "$token_output" ]]; then
  if proxmox-backup-manager user list-tokens backup@pbs --output-format json |
    jq -e '.[] | select(."token-name" == "afa")' >/dev/null; then
    proxmox-backup-manager user delete-token backup@pbs afa
  fi
  token_json="$(
    proxmox-backup-manager user generate-token backup@pbs afa \
      --comment "PVE host appdata backup token" \
      --output-format json
  )"
  token_value="$(jq -er '.value' <<<"$token_json")"
  umask 077
  printf '%s\n' "$token_value" >"$token_output"
fi

proxmox-backup-manager acl update /datastore/appdata DatastoreBackup \
  --auth-id backup@pbs
proxmox-backup-manager acl update /datastore/appdata DatastoreBackup \
  --auth-id 'backup@pbs!afa'

fingerprint="$(
  proxmox-backup-manager cert info |
    awk -F': ' '/Fingerprint \\(sha256\\)/ {print toupper($2)}'
)"
[[ -n "$fingerprint" ]] || {
  echo "Could not determine PBS TLS fingerprint." >&2
  exit 1
}
printf '%s\n' "$fingerprint" >/run/dothomelab-pbs.fingerprint

echo "PBS datastore, retention, verification, and backup identity are ready."
