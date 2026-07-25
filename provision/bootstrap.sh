#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly repo_root="$(cd -- "$script_dir/.." && pwd)"
# shellcheck disable=SC1091
source "$script_dir/inventory.env"

dry_run=false
skip_verify=false
restore_latest=false
env_source="/root/.env"
appdata_source=""

usage() {
  cat <<'EOF'
Usage: ./bootstrap.sh [options]

Build the declared homelab on an already installed Proxmox VE node.

Options:
  --dry-run                 Inspect prerequisites and print mutations only.
  --env-file PATH           Install PATH as /root/.env (default: /root/.env).
  --appdata-source PATH     Copy a recovered appdata tree into an empty dataset.
  --restore-latest          Restore the newest PBS appdata snapshot when empty.
  --skip-verify             Do not run focused end-to-end verifiers.
  -h, --help                Show this help.
EOF
}

while (($#)); do
  case "$1" in
    --dry-run)
      dry_run=true
      ;;
    --env-file)
      [[ $# -ge 2 ]] || {
        echo "--env-file requires a path" >&2
        exit 2
      }
      env_source="$2"
      shift
      ;;
    --appdata-source)
      [[ $# -ge 2 ]] || {
        echo "--appdata-source requires a path" >&2
        exit 2
      }
      appdata_source="$2"
      shift
      ;;
    --restore-latest)
      restore_latest=true
      ;;
    --skip-verify)
      skip_verify=true
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

print_command() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
}

run() {
  print_command "$@"
  "$dry_run" || "$@"
}

path_has_entries() {
  [[ -d "$1" ]] && [[ -n "$(find "$1" -mindepth 1 -maxdepth 1 -print -quit)" ]]
}

require_dataset_capacity() {
  local dataset="$1"
  local payload_bytes="$2"
  local description="$3"
  local available_bytes headroom_bytes required_bytes

  "$dry_run" && return 0
  available_bytes="$(zfs get -Hp -o value available "$dataset")"
  [[ "$available_bytes" =~ ^[0-9]+$ ]] ||
    die "Could not determine free capacity for $dataset"
  headroom_bytes=$((payload_bytes / 20 + 1024 * 1024 * 1024))
  required_bytes=$((payload_bytes + headroom_bytes))
  ((available_bytes >= required_bytes)) ||
    die "$description needs $required_bytes bytes including headroom; $dataset has $available_bytes"
}

require_commands() {
  local command_name
  for command_name in "$@"; do
    command -v "$command_name" >/dev/null ||
      die "Required command is missing: $command_name"
  done
}

install_host_prerequisites() {
  local missing=()
  local command_name
  for command_name in curl git jq openssl python3 rsync; do
    command -v "$command_name" >/dev/null || missing+=("$command_name")
  done
  ((${#missing[@]} == 0)) && return 0
  run apt-get update
  run env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git jq openssl python3 rsync
}

load_recovery_environment() {
  [[ -s "$env_source" ]] || die "Missing production environment: $env_source"
  if [[ "$env_source" != "/root/.env" ]]; then
    run install -m 0600 "$env_source" /root/.env
  else
    run chown 0:0 /root/.env
    run chmod 0600 /root/.env
  fi

  local effective_env="$env_source"
  local temporary_env=""
  if "$dry_run"; then
    temporary_env="$(mktemp /tmp/dothomelab-media-env.XXXXXX)"
    install -m 0600 "$env_source" "$temporary_env"
    "$repo_root/scripts/initialize-shelfarr-bookorbit-env.py" \
      --env-file "$temporary_env"
    "$repo_root/scripts/initialize-storyteller-env.py" \
      --env-file "$temporary_env"
    effective_env="$temporary_env"
  else
    "$repo_root/scripts/initialize-shelfarr-bookorbit-env.py" \
      --env-file /root/.env
    "$repo_root/scripts/initialize-storyteller-env.py" \
      --env-file /root/.env
    effective_env="/root/.env"
  fi
  # shellcheck disable=SC1091
  source "$repo_root/hosts/common/load-env.sh"
  load_dothomelab_env "$effective_env"
  [[ -z "$temporary_env" ]] || rm -f -- "$temporary_env"

  local required=(
    CLOUDFLARE_API_TOKEN
    DOMAINS
    BAR_ASSISTANT_MEILI_MASTER_KEY
    BOOKORBIT_ADMIN_PASSWORD
    BOOKORBIT_APP_URL
    BOOKORBIT_DB_PASSWORD
    BOOKORBIT_JWT_SECRET
    BOOKORBIT_OPDS_PASSWORD
    BOOKORBIT_SETUP_BOOTSTRAP_TOKEN
    HOMARR_SECRET_ENCRYPTION_KEY
    HA_BACKUP_PASSWORD
    IMMICHFRAME_API_KEY
    IMMICH_DB_DATABASE_NAME
    IMMICH_DB_DATA_LOCATION
    IMMICH_DB_USERNAME
    IMMICH_DB_PASSWORD
    IMMICH_EXTERNAL_LIBRARY_LOCATION
    IMMICH_UPLOAD_LOCATION
    IP6_PROVIDER
    JELLYSTAT_JWT_SECRET
    JELLYSTAT_POSTGRES_PASSWORD
    N8N_ADMIN_EMAIL
    N8N_ADMIN_FIRST_NAME
    N8N_ADMIN_LAST_NAME
    N8N_ADMIN_PASSWORD
    N8N_ENCRYPTION_KEY
    NZBGET_PASS
    NZBGET_USER
    PAPERLESS_ADMIN_MAIL
    PAPERLESS_ADMIN_PASSWORD
    PAPERLESS_ADMIN_USER
    PAPERLESS_DB_PASSWORD
    PAPERLESS_GPT_API_TOKEN
    PAPERLESS_GPT_OPENAI_API_KEY
    PAPERLESS_SECRET_KEY
    PROXIED
    PULSE_AUTH_PASS
    PULSE_AUTH_USER
    SERVARR_WIREGUARD_PRIVATE_KEY
    SHELFARR_ADMIN_PASSWORD
    SHELFARR_API_TOKEN
    SHELFARR_SECRET_KEY_BASE
    STORYTELLER_SECRET_KEY
    STORYTELLER_ADMIN_EMAIL
    STORYTELLER_ADMIN_FULL_NAME
    STORYTELLER_ADMIN_PASSWORD
    STORYTELLER_ADMIN_USERNAME
    SLSKD_API_KEY
    SLSKD_JWT_KEY
    SLSKD_SOULSEEK_PASSWORD
    SLSKD_SOULSEEK_USERNAME
    SLSKD_WEB_PASSWORD
    SLSKD_WEB_USERNAME
    SNAPOTTER_DB_PASSWORD
    SNAPOTTER_INITIAL_PASSWORD
    SNAPOTTER_INITIAL_USERNAME
    STIRLING_PDF_INITIAL_PASSWORD
    STIRLING_PDF_INITIAL_USERNAME
    SYNCTHING_GUI_PASSWORD
    SYNCTHING_GUI_USERNAME
    YTDLP_WEBUI_JWT_SECRET
    YTDLP_WEBUI_PASSWORD
    YTDLP_WEBUI_USERNAME
    ZOTERO_WEBDAV_PASSWORD
    ZOTERO_WEBDAV_USERNAME
  )
  local variable
  for variable in "${required[@]}"; do
    [[ -n "${!variable:-}" ]] || die "$variable is missing from $effective_env"
  done
  [[ "$PAPERLESS_GPT_API_TOKEN" =~ ^[[:xdigit:]]{40}$ ]] ||
    die "PAPERLESS_GPT_API_TOKEN must contain exactly 40 hexadecimal characters"
  [[ "${PAPERLESS_GPT_SERVICE_USER:-paperless-gpt}" != "$PAPERLESS_ADMIN_USER" ]] ||
    die "PAPERLESS_GPT_SERVICE_USER must differ from PAPERLESS_ADMIN_USER"
  [[ ${#BAR_ASSISTANT_MEILI_MASTER_KEY} -ge 32 ]] ||
    die "BAR_ASSISTANT_MEILI_MASTER_KEY must contain at least 32 characters"
  [[ ${#YTDLP_WEBUI_JWT_SECRET} -ge 32 ]] ||
    die "YTDLP_WEBUI_JWT_SECRET must contain at least 32 characters"
  [[ "$SLSKD_API_KEY" =~ ^[[:xdigit:]]{64}$ ]] ||
    die "SLSKD_API_KEY must contain exactly 64 hexadecimal characters"
  [[ "$SLSKD_JWT_KEY" =~ ^[[:xdigit:]]{64}$ ]] ||
    die "SLSKD_JWT_KEY must contain exactly 64 hexadecimal characters"
  [[ "$SLSKD_WEB_PASSWORD" =~ ^[[:xdigit:]]{64}$ ]] ||
    die "SLSKD_WEB_PASSWORD must contain exactly 64 hexadecimal characters"
  [[ "$SNAPOTTER_DB_PASSWORD" =~ ^[[:xdigit:]]{32,}$ ]] ||
    die "SNAPOTTER_DB_PASSWORD must contain at least 32 hexadecimal characters"
  [[ ${#SNAPOTTER_INITIAL_PASSWORD} -ge 20 ]] ||
    die "SNAPOTTER_INITIAL_PASSWORD must contain at least 20 characters"
  [[ ${#STIRLING_PDF_INITIAL_PASSWORD} -ge 20 ]] ||
    die "STIRLING_PDF_INITIAL_PASSWORD must contain at least 20 characters"
  if ! "$dry_run"; then
    [[ "$SHELFARR_SECRET_KEY_BASE" =~ ^[[:xdigit:]]{128}$ ]] ||
      die "SHELFARR_SECRET_KEY_BASE must contain exactly 128 hexadecimal characters"
    [[ ${#SHELFARR_ADMIN_PASSWORD} -ge 20 ]] ||
      die "SHELFARR_ADMIN_PASSWORD must contain at least 20 characters"
    [[ "$BOOKORBIT_DB_PASSWORD" =~ ^[[:xdigit:]]{32,}$ ]] ||
      die "BOOKORBIT_DB_PASSWORD must contain at least 32 hexadecimal characters"
    [[ "$BOOKORBIT_JWT_SECRET" =~ ^[[:xdigit:]]{64}$ ]] ||
      die "BOOKORBIT_JWT_SECRET must contain exactly 64 hexadecimal characters"
    [[ "$BOOKORBIT_SETUP_BOOTSTRAP_TOKEN" =~ ^[[:xdigit:]]{32,}$ ]] ||
      die "BOOKORBIT_SETUP_BOOTSTRAP_TOKEN must contain at least 32 hexadecimal characters"
    [[ ${#BOOKORBIT_ADMIN_PASSWORD} -ge 20 ]] ||
      die "BOOKORBIT_ADMIN_PASSWORD must contain at least 20 characters"
    [[ ${#BOOKORBIT_OPDS_PASSWORD} -ge 20 ]] ||
      die "BOOKORBIT_OPDS_PASSWORD must contain at least 20 characters"
  fi
  [[ "$SYNCTHING_GUI_USERNAME" =~ ^[A-Za-z0-9._-]{1,64}$ ]] ||
    die "SYNCTHING_GUI_USERNAME contains invalid characters"
  [[ ${#SYNCTHING_GUI_PASSWORD} -ge 32 ]] ||
    die "SYNCTHING_GUI_PASSWORD must contain at least 32 characters"
}

preflight() {
  [[ $EUID -eq 0 ]] || die "Run bootstrap as root on the Proxmox host."
  require_commands pveversion pct pveam pvesm zfs zpool

  local pve_version
  pve_version="$(pveversion | sed -n 's#pve-manager/\([0-9][0-9]*\).*#\1#p')"
  [[ "$pve_version" =~ ^[0-9]+$ && "$pve_version" -ge "$PVE_MIN_MAJOR" ]] ||
    die "Proxmox VE $PVE_MIN_MAJOR or newer is required."

  [[ "$(hostname -s)" == "$PVE_NODE_NAME" ]] ||
    die "Expected PVE node hostname $PVE_NODE_NAME, found $(hostname -s)"
  ip link show "$PVE_BRIDGE" >/dev/null ||
    die "Required bridge is missing: $PVE_BRIDGE"
  ip -4 address show dev "$PVE_BRIDGE" |
    grep -qE "[[:space:]]inet ${PVE_IP}/${LAN_PREFIX}([[:space:]]|$)" ||
    die "$PVE_BRIDGE must own $PVE_IP/$LAN_PREFIX before bootstrap"
  ip route show default |
    grep -qE "^default via ${LAN_GATEWAY}([[:space:]]|$)" ||
    die "Default gateway must be $LAN_GATEWAY"

  if ! "$dry_run"; then
    [[ -z "$(git -C "$repo_root" status --porcelain --untracked-files=normal)" ]] ||
      die "Commit repository changes before an apply run."
  fi
}

ensure_pool_imported() {
  local pool="$1"
  if zpool list -H -o name "$pool" >/dev/null 2>&1; then
    return 0
  fi
  zpool import | grep -qE "pool: ${pool}$" ||
    die "ZFS pool $pool is neither imported nor importable"
  run zpool import "$pool"
}

ensure_dataset() {
  local dataset="$1"
  shift
  if ! zfs list -H -o name "$dataset" >/dev/null 2>&1; then
    local mountpoint=""
    local index
    for ((index = 1; index <= $#; index += 2)); do
      if [[ "${!index}" == "mountpoint" ]]; then
        local value_index=$((index + 1))
        mountpoint="${!value_index}"
      fi
    done
    if [[ -n "$mountpoint" && "$mountpoint" != "none" ]] &&
      path_has_entries "$mountpoint"; then
      die "Refusing to shadow non-empty path $mountpoint with new dataset $dataset"
    fi

    local create_args=(zfs create)
    while (($#)); do
      create_args+=(-o "$1=$2")
      shift 2
    done
    create_args+=("$dataset")
    run "${create_args[@]}"
    return 0
  fi

  while (($#)); do
    run zfs set "$1=$2" "$dataset"
    shift 2
  done
}

ensure_top_ownership() {
  local path="$1"
  local expected_owner="$2"
  local mode="$3"
  local current_owner

  "$dry_run" && {
    log "Would verify $path owner=$expected_owner mode=$mode"
    return 0
  }
  current_owner="$(stat -c '%u:%g' "$path")"
  if [[ "$current_owner" != "$expected_owner" ]]; then
    path_has_entries "$path" &&
      die "$path is non-empty and owned by $current_owner, expected $expected_owner"
    run chown "$expected_owner" "$path"
  fi
  run chmod "$mode" "$path"
}

copy_recovered_appdata() {
  [[ -n "$appdata_source" ]] || return 0
  [[ -d "$appdata_source" ]] ||
    die "Appdata recovery source is not a directory: $appdata_source"
  [[ "$(realpath "$appdata_source")" != "$(realpath "$APPDATA_MOUNT")" ]] ||
    die "--appdata-source must differ from $APPDATA_MOUNT"
  if path_has_entries "$APPDATA_MOUNT"; then
    die "Refusing to copy appdata into non-empty $APPDATA_MOUNT"
  fi
  local source_kib
  source_kib="$(du -skx "$appdata_source" | awk '{print $1}')"
  [[ "$source_kib" =~ ^[0-9]+$ ]] ||
    die "Could not determine appdata recovery size"
  require_dataset_capacity \
    "$APPDATA_DATASET" "$((source_kib * 1024))" "Appdata copy"
  run rsync -aHAXS --numeric-ids --info=progress2 \
    "$appdata_source/" "$APPDATA_MOUNT/"
  run chown 101000:101000 "$APPDATA_MOUNT"
  run chmod 0755 "$APPDATA_MOUNT"
}

provision_storage() {
  ensure_pool_imported "$RPOOL_NAME"
  ensure_pool_imported "$VAULT_POOL_NAME"
  if ! "$dry_run" ||
    zpool list -H -o name "$VAULT_POOL_NAME" >/dev/null 2>&1; then
    [[ "$(zpool status -x)" == "all pools are healthy" ]] ||
      die "One or more imported ZFS pools are unhealthy"
  fi

  ensure_dataset "$APPDATA_PARENT_DATASET" \
    canmount off \
    mountpoint none
  ensure_dataset "$APPDATA_DATASET" \
    mountpoint "$APPDATA_MOUNT" \
    compression lz4 \
    atime off \
    xattr on \
    acltype posix
  ensure_dataset "$SHARED_DATASET" \
    mountpoint "$SHARED_MOUNT" \
    compression lz4 \
    atime off \
    xattr on \
    acltype posix \
    recordsize 1M
  ensure_dataset "$PBS_DATASET" \
    mountpoint "$PBS_MOUNT" \
    compression lz4 \
    quota "$PBS_DATASET_QUOTA"

  run zfs mount "$APPDATA_DATASET" 2>/dev/null || true
  run zfs mount "$SHARED_DATASET" 2>/dev/null || true
  run zfs mount "$PBS_DATASET" 2>/dev/null || true

  "$dry_run" || {
    [[ "$(findmnt -n -o SOURCE -T "$APPDATA_MOUNT")" == "$APPDATA_DATASET" ]] ||
      die "$APPDATA_MOUNT is not backed by $APPDATA_DATASET"
    [[ "$(findmnt -n -o SOURCE -T "$SHARED_MOUNT")" == "$SHARED_DATASET" ]] ||
      die "$SHARED_MOUNT is not backed by $SHARED_DATASET"
    [[ "$(findmnt -n -o SOURCE -T "$PBS_MOUNT")" == "$PBS_DATASET" ]] ||
      die "$PBS_MOUNT is not backed by $PBS_DATASET"
  }

  ensure_top_ownership "$APPDATA_MOUNT" "101000:101000" 0755
  ensure_top_ownership "$SHARED_MOUNT" "101000:101000" 0775
  ensure_top_ownership "$PBS_MOUNT" "100034:100034" 0750
  if [[ ! -d "$YTDLP_DOWNLOADS_HOST_PATH" ]]; then
    run install -d -o 101000 -g 101000 -m 0750 \
      "$YTDLP_DOWNLOADS_HOST_PATH"
  fi
  ensure_top_ownership \
    "$YTDLP_DOWNLOADS_HOST_PATH" "101000:101000" 0750
  if [[ ! -d "$SLSKD_MUSIC_HOST_PATH" ]]; then
    run install -d -o 101000 -g 101000 -m 0750 \
      "$SLSKD_MUSIC_HOST_PATH"
  fi
  if [[ ! -d "$SLSKD_DOWNLOADS_HOST_PATH" ]]; then
    run install -d -o 101000 -g 101000 -m 0750 \
      "$SLSKD_DOWNLOADS_HOST_PATH"
  fi
  ensure_top_ownership \
    "$SLSKD_DOWNLOADS_HOST_PATH" "101000:101000" 0750
  if [[ ! -d "$AUDIOBOOKSHELF_PODCASTS_HOST_PATH" ]]; then
    run install -d -o 101000 -g 101000 -m 0755 \
      "$AUDIOBOOKSHELF_PODCASTS_HOST_PATH"
  fi
  "$dry_run" || {
    setpriv --reuid=101000 --regid=101000 --clear-groups \
      test -r "$SLSKD_MUSIC_HOST_PATH" &&
      setpriv --reuid=101000 --regid=101000 --clear-groups \
        test -w "$SLSKD_MUSIC_HOST_PATH" ||
      die "Apps UID/GID 1000:1000 cannot manage $SLSKD_MUSIC_HOST_PATH"
    [[ "$(findmnt -n -o SOURCE -T "$SLSKD_MUSIC_HOST_PATH")" == "$SHARED_DATASET" ]] &&
      [[ "$(findmnt -n -o SOURCE -T "$SLSKD_DOWNLOADS_HOST_PATH")" == "$SHARED_DATASET" ]] ||
      die "slskd music and downloads are not backed by $SHARED_DATASET"
    [[ "$(stat -c '%d' "$SLSKD_MUSIC_HOST_PATH")" == "$(stat -c '%d' "$SLSKD_DOWNLOADS_HOST_PATH")" ]] ||
      die "slskd music and downloads are not on the same filesystem"
    [[ "$(findmnt -n -o SOURCE -T "$AUDIOBOOKSHELF_PODCASTS_HOST_PATH")" == "$SHARED_DATASET" ]] ||
      die "Audiobookshelf podcasts are not backed by $SHARED_DATASET"
    setpriv --reuid=101000 --regid=101000 --clear-groups \
      test -w "$AUDIOBOOKSHELF_PODCASTS_HOST_PATH" ||
      die "Apps UID/GID 1000:1000 cannot write $AUDIOBOOKSHELF_PODCASTS_HOST_PATH"
  }
  copy_recovered_appdata
}

prepare_media_contract() {
  if "$dry_run"; then
    "$repo_root/provision/prepare-media-contract.sh" --dry-run
  else
    "$repo_root/provision/prepare-media-contract.sh"
  fi
}

ensure_template() {
  local requested="$1"
  local major="$2"
  local local_ref="$PVE_TEMPLATE_STORAGE:vztmpl/$requested"

  if pveam list "$PVE_TEMPLATE_STORAGE" |
    awk 'NR > 1 {print $1}' | grep -qx "$local_ref"; then
    ENSURED_TEMPLATE="$local_ref"
    return 0
  fi

  if "$dry_run"; then
    log "Would download LXC template $requested"
    ENSURED_TEMPLATE="$local_ref"
    return 0
  fi

  run pveam update
  local available
  available="$(
    pveam available --section system |
      awk -v exact="$requested" '$2 == exact {print $2; exit}'
  )"
  if [[ -z "$available" ]]; then
    available="$(
      pveam available --section system |
        awk -v pattern="debian-" "$2 ~ pattern {print $2}" |
        grep -E "^debian-${major}-standard_.*_amd64\\.tar\\.(zst|gz)$" |
        sort -V |
        tail -1
    )"
  fi
  [[ -n "$available" ]] ||
    die "No Debian $major LXC template is available from pveam"
  run pveam download "$PVE_TEMPLATE_STORAGE" "$available"
  ENSURED_TEMPLATE="$PVE_TEMPLATE_STORAGE:vztmpl/$available"
}

CT_CREATED=()

wait_for_guest() {
  local ctid="$1"
  local attempt
  for attempt in {1..60}; do
    pct exec "$ctid" -- true >/dev/null 2>&1 && return 0
    sleep 1
  done
  die "LXC $ctid did not become ready"
}

validate_existing_guest() {
  local ctid="$1"
  local config
  config="$(pct config "$ctid")"
  local expected
  for expected in \
    "arch: amd64" \
    "cores: ${CT_CORES[$ctid]}" \
    "hostname: ${CT_HOSTNAME[$ctid]}" \
    "ostype: debian" \
    "swap: ${CT_SWAP[$ctid]}" \
    "unprivileged: 1"; do
    grep -qx "$expected" <<<"$config" ||
      die "LXC $ctid does not match declared setting: $expected"
  done
  local current_memory
  current_memory="$(
    awk -F': ' '$1 == "memory" {print $2; exit}' <<<"$config"
  )"
  if [[ "$ctid" == "112" ]]; then
    [[ "$current_memory" =~ ^[0-9]+$ ]] ||
      die "LXC 112 has an unreadable memory declaration"
    ((current_memory <= CT_MEMORY[$ctid])) ||
      die "LXC 112 memory $current_memory exceeds declared ${CT_MEMORY[$ctid]}"
    if ((current_memory < CT_MEMORY[$ctid])); then
      log "NOTICE: LXC 112 memory will increase from $current_memory to ${CT_MEMORY[$ctid]} MiB"
    fi
  else
    [[ "$current_memory" == "${CT_MEMORY[$ctid]}" ]] ||
      die "LXC $ctid does not match declared memory ${CT_MEMORY[$ctid]}"
  fi
  grep -qE \
    "^rootfs: ${PVE_ROOTFS_STORAGE}:.*[,]size=${CT_ROOTFS_GB[$ctid]}G(,|$)" \
    <<<"$config" ||
    die "LXC $ctid root disk does not match the declared storage and size"
  grep -qE \
    "^net0: .*bridge=${PVE_BRIDGE}.*hwaddr=${CT_MAC[$ctid]}([,]|$)" \
    <<<"$config" ||
    die "LXC $ctid bridge or MAC address drifted"

  case "$ctid" in
    102)
      grep -Fqx "features: nesting=1" <<<"$config" &&
        grep -Fqx "mp0: $SHARED_MOUNT,mp=/data" <<<"$config" &&
        grep -Fqx "mp1: $APPDATA_MOUNT,mp=/docker" <<<"$config" ||
        die "LXC 102 feature or bind-mount declaration drifted"
      ;;
    110)
      grep -Fqx "features: nesting=1" <<<"$config" &&
        grep -Fqx "mp0: $APPDATA_MOUNT,mp=/srv/appdata/docker" <<<"$config" &&
        grep -Fqx "mp1: $SHARED_MOUNT,mp=/vault/shared" <<<"$config" ||
        die "LXC 110 feature or bind-mount declaration drifted"
      ;;
    112)
      grep -Fqx "features: nesting=1" <<<"$config" &&
        grep -Fqx "dev0: $APPS_DRI_RENDER,gid=104" <<<"$config" &&
        grep -Fqx "dev1: $APPS_DRI_CARD,gid=44" <<<"$config" &&
        grep -Fqx "mp0: $SHARED_MOUNT,mp=/data,ro=1" <<<"$config" &&
        grep -Fqx "mp1: $APPDATA_MOUNT,mp=/srv/appdata/docker" <<<"$config" ||
        die "LXC 112 feature, GPU, or bind-mount declaration drifted"
      if grep -q '^mp2:' <<<"$config"; then
        grep -Fqx \
          "mp2: $YTDLP_DOWNLOADS_HOST_PATH,mp=$YTDLP_DOWNLOADS_GUEST_PATH" \
          <<<"$config" ||
          die "LXC 112 mp2 conflicts with the yt-dlp downloads mount"
      else
        log "NOTICE: existing LXC 112 is missing the additive yt-dlp downloads mount"
      fi
      if grep -q '^mp3:' <<<"$config"; then
        grep -Fqx \
          "mp3: $SLSKD_MUSIC_HOST_PATH,mp=$SLSKD_MUSIC_GUEST_PATH" \
          <<<"$config" ||
          die "LXC 112 mp3 conflicts with the slskd music mount"
      else
        log "NOTICE: existing LXC 112 is missing the additive slskd music mount"
      fi
      if grep -q '^mp4:' <<<"$config"; then
        grep -Fqx \
          "mp4: $SLSKD_DOWNLOADS_HOST_PATH,mp=$SLSKD_DOWNLOADS_GUEST_PATH" \
          <<<"$config" ||
          die "LXC 112 mp4 conflicts with the slskd downloads mount"
      else
        log "NOTICE: existing LXC 112 is missing the additive slskd downloads mount"
      fi
      if grep -q '^mp5:' <<<"$config"; then
        grep -Fqx \
          "mp5: $AUDIOBOOKSHELF_PODCASTS_HOST_PATH,mp=$AUDIOBOOKSHELF_PODCASTS_GUEST_PATH" \
          <<<"$config" ||
          die "LXC 112 mp5 conflicts with the Audiobookshelf podcasts mount"
      else
        log "NOTICE: existing LXC 112 is missing the additive Audiobookshelf podcasts mount"
      fi
      if grep -q '^mp6:' <<<"$config"; then
        grep -Fqx \
          "mp6: $STORYTELLER_SHARED_HOST_PATH,mp=$STORYTELLER_SHARED_GUEST_PATH" \
          <<<"$config" ||
          die "LXC 112 mp6 conflicts with the Storyteller shared mount"
      else
        log "NOTICE: existing LXC 112 is missing the additive Storyteller shared mount"
      fi
      ;;
    113)
      grep -Fqx "features: nesting=1,keyctl=1" <<<"$config" &&
        grep -Fqx "mp0: $PBS_MOUNT,mp=/mnt/datastore/appdata" <<<"$config" ||
        die "LXC 113 feature or bind-mount declaration drifted"
      ;;
  esac

  if ! grep -q "ip=${CT_IP[$ctid]}/${LAN_PREFIX}" <<<"$config"; then
    grep -q "ip=dhcp" <<<"$config" ||
      die "LXC $ctid has an unexpected IPv4 definition"
    log "NOTICE: existing LXC $ctid keeps DHCP; clean rebuilds use static ${CT_IP[$ctid]}"
  fi
}

create_guest() {
  local ctid="$1"
  local template="$2"
  local features="nesting=1"
  local tags="dothomelab"
  [[ "$ctid" == "113" ]] && {
    features="nesting=1,keyctl=1"
    tags="backup;dothomelab"
  }

  if pct config "$ctid" >/dev/null 2>&1; then
    CT_CREATED[$ctid]=false
    validate_existing_guest "$ctid"
    if [[ "$ctid" == "112" ]] &&
      ! pct config "$ctid" |
        grep -Fqx "memory: ${CT_MEMORY[$ctid]}"; then
      run pct set "$ctid" --memory "${CT_MEMORY[$ctid]}"
    fi
    if [[ "$ctid" == "112" ]] &&
      ! pct config "$ctid" |
        grep -Fqx \
          "mp2: $YTDLP_DOWNLOADS_HOST_PATH,mp=$YTDLP_DOWNLOADS_GUEST_PATH"; then
      run pct set "$ctid" \
        --mp2 "$YTDLP_DOWNLOADS_HOST_PATH,mp=$YTDLP_DOWNLOADS_GUEST_PATH"
    fi
    if [[ "$ctid" == "112" ]] &&
      ! pct config "$ctid" |
        grep -Fqx \
          "mp3: $SLSKD_MUSIC_HOST_PATH,mp=$SLSKD_MUSIC_GUEST_PATH"; then
      run pct set "$ctid" \
        --mp3 "$SLSKD_MUSIC_HOST_PATH,mp=$SLSKD_MUSIC_GUEST_PATH"
    fi
    if [[ "$ctid" == "112" ]] &&
      ! pct config "$ctid" |
        grep -Fqx \
          "mp4: $SLSKD_DOWNLOADS_HOST_PATH,mp=$SLSKD_DOWNLOADS_GUEST_PATH"; then
      run pct set "$ctid" \
        --mp4 "$SLSKD_DOWNLOADS_HOST_PATH,mp=$SLSKD_DOWNLOADS_GUEST_PATH"
    fi
    if [[ "$ctid" == "112" ]] &&
      ! pct config "$ctid" |
        grep -Fqx \
          "mp5: $AUDIOBOOKSHELF_PODCASTS_HOST_PATH,mp=$AUDIOBOOKSHELF_PODCASTS_GUEST_PATH"; then
      run pct set "$ctid" \
        --mp5 "$AUDIOBOOKSHELF_PODCASTS_HOST_PATH,mp=$AUDIOBOOKSHELF_PODCASTS_GUEST_PATH"
    fi
    if [[ "$ctid" == "112" ]] &&
      ! pct config "$ctid" |
        grep -Fqx \
          "mp6: $STORYTELLER_SHARED_HOST_PATH,mp=$STORYTELLER_SHARED_GUEST_PATH"; then
      run pct set "$ctid" \
        --mp6 "$STORYTELLER_SHARED_HOST_PATH,mp=$STORYTELLER_SHARED_GUEST_PATH"
    fi
    if ! pct status "$ctid" | grep -q "status: running"; then
      run pct start "$ctid"
      "$dry_run" || wait_for_guest "$ctid"
    fi
    return 0
  fi

  CT_CREATED[$ctid]=true
  local args=(
    pct create "$ctid" "$template"
    --arch amd64
    --cores "${CT_CORES[$ctid]}"
    --features "$features"
    --hostname "${CT_HOSTNAME[$ctid]}"
    --memory "${CT_MEMORY[$ctid]}"
    --net0 "name=eth0,bridge=$PVE_BRIDGE,firewall=1,hwaddr=${CT_MAC[$ctid]},ip=${CT_IP[$ctid]}/$LAN_PREFIX,gw=$LAN_GATEWAY,type=veth"
    --nameserver "$BOOTSTRAP_DNS"
    --onboot 1
    --ostype debian
    --rootfs "$PVE_ROOTFS_STORAGE:${CT_ROOTFS_GB[$ctid]}"
    --start 1
    --startup "order=${CT_STARTUP_ORDER[$ctid]},up=10"
    --storage "$PVE_ROOTFS_STORAGE"
    --swap "${CT_SWAP[$ctid]}"
    --tags "$tags"
    --timezone Europe/Amsterdam
    --unprivileged 1
  )

  case "$ctid" in
    102)
      [[ -c "$SERVARR_TUN_DEVICE" ]] ||
        die "Missing Servarr TUN device: $SERVARR_TUN_DEVICE"
      args+=(
        --dev0 "path=$SERVARR_TUN_DEVICE"
        --mp0 "$SHARED_MOUNT,mp=/data"
        --mp1 "$APPDATA_MOUNT,mp=/docker"
      )
      ;;
    110)
      [[ -c "$INFRA_TUN_DEVICE" ]] ||
        die "Missing Infra TUN device: $INFRA_TUN_DEVICE"
      args+=(
        --dev0 "path=$INFRA_TUN_DEVICE"
        --mp0 "$APPDATA_MOUNT,mp=/srv/appdata/docker"
        --mp1 "$SHARED_MOUNT,mp=/vault/shared"
      )
      ;;
    112)
      [[ -e "$APPS_DRI_CARD" && -e "$APPS_DRI_RENDER" ]] ||
        die "Apps GPU devices are missing: $APPS_DRI_CARD $APPS_DRI_RENDER"
      args+=(
        --dev0 "path=$APPS_DRI_RENDER,gid=104"
        --dev1 "path=$APPS_DRI_CARD,gid=44"
        --mp0 "$SHARED_MOUNT,mp=/data,ro=1"
        --mp1 "$APPDATA_MOUNT,mp=/srv/appdata/docker"
        --mp2 "$YTDLP_DOWNLOADS_HOST_PATH,mp=$YTDLP_DOWNLOADS_GUEST_PATH"
        --mp3 "$SLSKD_MUSIC_HOST_PATH,mp=$SLSKD_MUSIC_GUEST_PATH"
        --mp4 "$SLSKD_DOWNLOADS_HOST_PATH,mp=$SLSKD_DOWNLOADS_GUEST_PATH"
        --mp5 "$AUDIOBOOKSHELF_PODCASTS_HOST_PATH,mp=$AUDIOBOOKSHELF_PODCASTS_GUEST_PATH"
        --mp6 "$STORYTELLER_SHARED_HOST_PATH,mp=$STORYTELLER_SHARED_GUEST_PATH"
      )
      ;;
    113)
      args+=(
        --mp0 "$PBS_MOUNT,mp=/mnt/datastore/appdata"
        --protection 0
      )
      ;;
    *)
      die "No guest definition for LXC $ctid"
      ;;
  esac

  run "${args[@]}"
  "$dry_run" || wait_for_guest "$ctid"
}

sync_guest_repo() {
  local ctid="$1"
  run "$repo_root/scripts/sync-guest-repo.sh" "$ctid"
}

guest_exec() {
  local ctid="$1"
  shift
  run pct exec "$ctid" -- "$@"
}

guest_exec_with_env() {
  local ctid="$1"
  shift
  if "$dry_run"; then
    print_command pct push "$ctid" /root/.env /run/dothomelab.env --perms 0600
    print_command pct exec "$ctid" -- env DOTHOMELAB_ENV=/run/dothomelab.env "$@"
    return 0
  fi

  pct push "$ctid" /root/.env /run/dothomelab.env --perms 0600
  if ! pct exec "$ctid" -- env DOTHOMELAB_ENV=/run/dothomelab.env "$@"; then
    pct exec "$ctid" -- rm -f /run/dothomelab.env >/dev/null 2>&1 || true
    return 1
  fi
  pct exec "$ctid" -- rm -f /run/dothomelab.env
}

provision_pbs_guest() {
  sync_guest_repo 113
  local request_token=""
  if [[ "${CT_CREATED[113]:-false}" == "true" ||
    ! -s /etc/dothomelab/pbs-appdata.token ]]; then
    request_token="/run/dothomelab-pbs.token"
  fi

  guest_exec_with_env 113 \
    bash -lc \
    "exec /opt/dothomelab/hosts/pbs/install.sh \"\$DOTHOMELAB_ENV\" '$request_token'"

  "$dry_run" && return 0
  install -d -m 0700 /etc/dothomelab
  local temp_fingerprint temp_token=""
  temp_fingerprint="$(mktemp /tmp/dothomelab-pbs-fingerprint.XXXXXX)"
  cleanup_pbs_pulls() {
    rm -f -- "$temp_fingerprint"
    [[ -z "$temp_token" ]] || rm -f -- "$temp_token"
  }
  trap cleanup_pbs_pulls RETURN
  pct pull 113 /run/dothomelab-pbs.fingerprint "$temp_fingerprint"
  PBS_LIVE_FINGERPRINT="$(<"$temp_fingerprint")"
  [[ -n "$PBS_LIVE_FINGERPRINT" ]] ||
    die "PBS did not return a certificate fingerprint"

  if [[ -n "$request_token" ]]; then
    temp_token="$(mktemp /tmp/dothomelab-pbs-token.XXXXXX)"
    pct pull 113 "$request_token" "$temp_token"
    install -m 0600 "$temp_token" /etc/dothomelab/pbs-appdata.token
    rm -f -- "$temp_token"
    temp_token=""
    pct exec 113 -- rm -f "$request_token"
  fi
  pct set 113 --protection 1
  cleanup_pbs_pulls
  trap - RETURN
}

ensure_pbs_encryption_key() {
  local target="/etc/dothomelab/pbs-appdata.key"
  [[ -s "$target" ]] && return 0
  "$dry_run" && {
    log "Would install or create the PBS client encryption key at $target"
    return 0
  }

  if [[ -n "${PBS_ENCRYPTION_KEY_FILE:-}" ]]; then
    [[ -s "$PBS_ENCRYPTION_KEY_FILE" ]] ||
      die "PBS_ENCRYPTION_KEY_FILE is unreadable: $PBS_ENCRYPTION_KEY_FILE"
    install -m 0600 "$PBS_ENCRYPTION_KEY_FILE" "$target"
    return 0
  fi
  if [[ -s "$APPDATA_MOUNT/recovery/pbs-appdata.key" ]]; then
    install -m 0600 "$APPDATA_MOUNT/recovery/pbs-appdata.key" "$target"
    return 0
  fi
  if [[ -n "${PBS_ENCRYPTION_KEY_B64:-}" ]]; then
    umask 077
    printf '%s' "$PBS_ENCRYPTION_KEY_B64" | base64 --decode >"$target"
    [[ -s "$target" ]] || die "PBS_ENCRYPTION_KEY_B64 decoded to an empty file"
    return 0
  fi
  if path_has_entries "$PBS_MOUNT/host"; then
    die "Existing encrypted PBS snapshots require PBS_ENCRYPTION_KEY_FILE or PBS_ENCRYPTION_KEY_B64"
  fi
  proxmox-backup-client key create "$target" --kdf none
  chmod 0600 "$target"
}

install_host_backup() {
  ensure_pbs_encryption_key
  "$dry_run" && {
    log "Would install PVE backup client configuration and systemd units"
    return 0
  }

  [[ -n "${PBS_LIVE_FINGERPRINT:-}" ]] || {
    local temp_fingerprint
    temp_fingerprint="$(mktemp /tmp/dothomelab-pbs-fingerprint.XXXXXX)"
    pct pull 113 /run/dothomelab-pbs.fingerprint "$temp_fingerprint"
    PBS_LIVE_FINGERPRINT="$(<"$temp_fingerprint")"
    rm -f -- "$temp_fingerprint"
  }

  install -d -m 0700 \
    /etc/dothomelab \
    /etc/dothomelab/backup-pre.d \
    /etc/dothomelab/backup-post.d
  install -m 0600 /dev/stdin /etc/dothomelab/pbs-appdata.conf <<EOF
APPDATA_DATASET="$APPDATA_DATASET"
APPDATA_MOUNT="$APPDATA_MOUNT"
PBS_BACKUP_ID="afa-appdata"
PBS_REPOSITORY="backup@pbs!afa@${CT_IP[113]}:appdata"
PBS_FINGERPRINT="$PBS_LIVE_FINGERPRINT"
PBS_PASSWORD_FILE="/etc/dothomelab/pbs-appdata.token"
PBS_KEY_FILE="/etc/dothomelab/pbs-appdata.key"
RECOVERY_ENV_FILE="/root/.env"
QUIESCE_CTIDS="102 110 112"
PRE_HOOK_DIR="/etc/dothomelab/backup-pre.d"
POST_HOOK_DIR="/etc/dothomelab/backup-post.d"
EOF

  install -m 0755 \
    "$repo_root/backup/pbs/appdata-backup.sh" \
    /usr/local/sbin/dothomelab-appdata-backup
  install -m 0755 \
    "$repo_root/backup/pbs/restore-appdata.sh" \
    /usr/local/sbin/dothomelab-restore-appdata
  install -m 0755 \
    "$repo_root/backup/pbs/wud-update.sh" \
    /usr/local/sbin/dothomelab-wud-update
  install -m 0755 \
    "$repo_root/hosts/haos/backup-vm.sh" \
    /usr/local/sbin/dothomelab-haos-backup
  install -m 0644 \
    "$repo_root/provision/inventory.env" \
    /etc/dothomelab/inventory.env
  install -m 0755 \
    "$repo_root/backup/pbs/paperless-database-backup.sh" \
    /etc/dothomelab/backup-pre.d/20-paperless-database
  install -m 0755 \
    "$repo_root/backup/pbs/snapotter-database-backup.sh" \
    /etc/dothomelab/backup-pre.d/30-snapotter-database
  install -m 0755 \
    "$repo_root/backup/pbs/bookorbit-database-backup.sh" \
    /etc/dothomelab/backup-pre.d/40-bookorbit-database
  install -m 0755 \
    "$repo_root/backup/pbs/storyteller-database-backup.sh" \
    /etc/dothomelab/backup-pre.d/50-storyteller-database
  install -m 0644 \
    "$repo_root/backup/pbs/dothomelab-appdata-backup.service" \
    "$repo_root/backup/pbs/dothomelab-appdata-backup.timer" \
    "$repo_root/backup/pbs/dothomelab-wud-update.service" \
    /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable dothomelab-appdata-backup.timer
}

enable_host_backup_timer() {
  run systemctl enable --now dothomelab-appdata-backup.timer
}

restore_latest_appdata() {
  "$restore_latest" || return 0
  path_has_entries "$APPDATA_MOUNT" &&
    die "--restore-latest requires empty $APPDATA_MOUNT"
  "$dry_run" && {
    log "Would restore the newest PBS appdata snapshot into the empty dataset"
    return 0
  }

  # shellcheck disable=SC1091
  source /etc/dothomelab/pbs-appdata.conf
  export PBS_REPOSITORY PBS_FINGERPRINT PBS_PASSWORD_FILE
  local snapshot snapshot_size
  IFS=$'\t' read -r snapshot snapshot_size < <(
    proxmox-backup-client snapshot list --output-format json |
      python3 -c '
import datetime
import json
import sys
items = [
    item for item in json.load(sys.stdin)
    if item.get("backup-type") == "host" and item.get("backup-id") == "afa-appdata"
]
if not items:
    raise SystemExit("no afa-appdata snapshots found")
item = max(items, key=lambda value: value["backup-time"])
stamp = datetime.datetime.fromtimestamp(
    item["backup-time"], datetime.timezone.utc
).strftime("%Y-%m-%dT%H:%M:%SZ")
print(
    "host/{}/{}".format(item["backup-id"], stamp),
    item["size"],
    sep="\t",
)
'
  )
  [[ -n "$snapshot" ]] || die "Could not select the latest PBS snapshot"
  [[ "$snapshot_size" =~ ^[0-9]+$ ]] ||
    die "Could not determine the size of $snapshot"
  require_dataset_capacity \
    "$APPDATA_PARENT_DATASET" "$snapshot_size" "PBS appdata restore"

  local suffix temp_dataset temp_mount
  suffix="$(date --utc +%Y%m%dT%H%M%SZ)"
  temp_dataset="$APPDATA_PARENT_DATASET/restore-$suffix"
  temp_mount="/srv/dothomelab-appdata-restore-$suffix"
  zfs create -o mountpoint="$temp_mount" -o compression=lz4 "$temp_dataset"

  cleanup_restore_dataset() {
    if zfs list -H -o name "$temp_dataset" >/dev/null 2>&1; then
      zfs destroy "$temp_dataset"
    fi
  }
  trap cleanup_restore_dataset RETURN

  proxmox-backup-client restore \
    "$snapshot" appdata.pxar "$temp_mount/payload" \
    --keyfile /etc/dothomelab/pbs-appdata.key \
    --repository "$PBS_REPOSITORY"
  find "$temp_mount/payload" -mindepth 1 -maxdepth 1 \
    -exec mv -t "$temp_mount" -- {} +
  rmdir "$temp_mount/payload"

  path_has_entries "$APPDATA_MOUNT" &&
    die "Canonical appdata became non-empty during restore"
  zfs destroy "$APPDATA_DATASET"
  zfs rename "$temp_dataset" "$APPDATA_DATASET"
  trap - RETURN
  zfs set \
    mountpoint="$APPDATA_MOUNT" \
    compression=lz4 \
    atime=off \
    xattr=on \
    acltype=posix \
    "$APPDATA_DATASET"
  zfs mount "$APPDATA_DATASET" 2>/dev/null || true
  [[ "$(findmnt -n -o SOURCE -T "$APPDATA_MOUNT")" == "$APPDATA_DATASET" ]] ||
    die "Restored $APPDATA_DATASET did not mount at $APPDATA_MOUNT"
  chown 101000:101000 "$APPDATA_MOUNT"
  chmod 0755 "$APPDATA_MOUNT"
  log "Restored $snapshot into $APPDATA_DATASET"
}

require_recovered_appdata() {
  "$dry_run" && return 0
  path_has_entries "$APPDATA_MOUNT" ||
    die "$APPDATA_MOUNT is empty; supply --appdata-source or --restore-latest"
}

restore_haos_vm() {
  run "$repo_root/hosts/haos/restore-vm.sh"
  run "$repo_root/hosts/haos/configure-proxy.sh"
}

restore_pbs_admin_credential() {
  [[ -n "${PBS_ROOT_PASSWORD:-}" ]] && return 0
  local hash_file="$APPDATA_MOUNT/recovery/pbs-root.shadow-hash"
  [[ -s "$hash_file" ]] ||
    die "Set PBS_ROOT_PASSWORD or recover $hash_file before completing bootstrap"
  if "$dry_run"; then
    log "Would restore the PBS root password hash from appdata"
    return 0
  fi

  pct push 113 "$hash_file" /run/dothomelab-pbs-root.hash --perms 0600
  pct exec 113 -- bash -euc '
    hash="$(< /run/dothomelab-pbs-root.hash)"
    [[ -n "$hash" ]]
    usermod --password "$hash" root
    rm -f /run/dothomelab-pbs-root.hash
  '
}

provision_application_guests() {
  local ctid
  for ctid in "${APPLICATION_CTIDS[@]}"; do
    create_guest "$ctid" "$DEBIAN12_REF"
    sync_guest_repo "$ctid"
    guest_exec "$ctid" \
      /opt/dothomelab/hosts/common/bootstrap-docker.sh
  done
}

install_docker_api_tls() {
  local pki_dir="/etc/dothomelab/docker-api-pki"
  if [[ ! -d "$pki_dir" ]]; then
    run "$repo_root/scripts/generate-docker-api-pki.sh" "$pki_dir"
  fi
  "$dry_run" && {
    log "Would install Docker mTLS server and WUD client certificates"
    return 0
  }

  local required=(
    "$pki_dir/ca.pem"
    "$pki_dir/apps/server-cert.pem"
    "$pki_dir/apps/key.pem"
    "$pki_dir/servarr/server-cert.pem"
    "$pki_dir/servarr/key.pem"
    "$pki_dir/client/client-cert.pem"
    "$pki_dir/client/key.pem"
  )
  local file
  for file in "${required[@]}"; do
    [[ -s "$file" ]] || die "Incomplete Docker API PKI: $file"
  done

  for ctid in 102 112; do
    pct exec "$ctid" -- install -d -m 0700 /etc/docker/tls
    pct push "$ctid" "$pki_dir/ca.pem" /etc/docker/tls/ca.pem --perms 0444
  done
  pct push 102 "$pki_dir/servarr/server-cert.pem" \
    /etc/docker/tls/server-cert.pem --perms 0444
  pct push 102 "$pki_dir/servarr/key.pem" \
    /etc/docker/tls/server-key.pem --perms 0400
  pct push 112 "$pki_dir/apps/server-cert.pem" \
    /etc/docker/tls/server-cert.pem --perms 0444
  pct push 112 "$pki_dir/apps/key.pem" \
    /etc/docker/tls/server-key.pem --perms 0400

  pct exec 110 -- install -d -m 0700 /etc/dothomelab/wud-docker-api
  pct push 110 "$pki_dir/ca.pem" \
    /etc/dothomelab/wud-docker-api/ca.pem --perms 0444
  pct push 110 "$pki_dir/client/client-cert.pem" \
    /etc/dothomelab/wud-docker-api/client-cert.pem --perms 0444
  pct push 110 "$pki_dir/client/key.pem" \
    /etc/dothomelab/wud-docker-api/client-key.pem --perms 0400

  pct exec 102 -- /opt/dothomelab/hosts/common/docker-api/install.sh \
    /opt/dothomelab/hosts/servarr/docker-api/20-dothomelab-remote-api.conf
  pct exec 112 -- /opt/dothomelab/hosts/common/docker-api/install.sh \
    /opt/dothomelab/hosts/apps/docker-api/20-dothomelab-remote-api.conf
}

prepare_native_and_storage() {
  guest_exec 102 /opt/dothomelab/hosts/servarr/hello/prepare.sh
  guest_exec 102 /opt/dothomelab/hosts/servarr/shelfarr/prepare.sh

  guest_exec 110 /opt/dothomelab/hosts/infra/services/prepare.sh
  guest_exec_with_env 110 \
    bash -lc \
    'source /opt/dothomelab/hosts/common/load-env.sh; load_dothomelab_env "$DOTHOMELAB_ENV"; exec /opt/dothomelab/hosts/infra/cockpit/install.sh'
  guest_exec_with_env 110 \
    bash -lc \
    'source /opt/dothomelab/hosts/common/load-env.sh; load_dothomelab_env "$DOTHOMELAB_ENV"; exec /opt/dothomelab/hosts/infra/tailscale/install.sh'
  guest_exec 110 /opt/dothomelab/hosts/infra/obsidian-sync/prepare.sh
  guest_exec 110 /opt/dothomelab/hosts/infra/n8n/prepare.sh
  guest_exec 110 /opt/dothomelab/hosts/infra/pulse/prepare.sh
  guest_exec 110 install -d -o 1000 -g 1000 -m 0750 \
    /srv/appdata/docker/wud/store
  guest_exec 110 systemctl enable --now dothomelab-pihole-ip.service

  guest_exec 112 /opt/dothomelab/hosts/apps/immich/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/audiobookshelf/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/bar-assistant/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/bookorbit/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/storyteller/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/slskd/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/droppedneedle/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/immichframe/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/kavita/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/loki/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/media/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/mealie/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/paperless-ngx/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/paperless-gpt/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/prometheus/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/services/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/snapotter/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/stirling-pdf/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/zotero-webdav/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/wizarr/prepare.sh
  guest_exec 112 /opt/dothomelab/hosts/apps/yt-dlp-web-ui/prepare.sh
}

deploy_projects() {
  run "$repo_root/scripts/deploy-compose.sh" 110 \
    hosts/infra/services/compose.yaml
  guest_exec 110 \
    /opt/dothomelab/hosts/infra/services/configure-pihole-dns.py
  run "$repo_root/scripts/deploy-compose.sh" 110 \
    hosts/infra/obsidian-sync/compose.yaml
  guest_exec_with_env 110 \
    /opt/dothomelab/hosts/infra/obsidian-sync/configure-syncthing.sh
  run "$repo_root/scripts/deploy-compose.sh" 110 \
    hosts/infra/n8n/compose.yaml
  guest_exec_with_env 110 \
    bash -lc \
    'source /opt/dothomelab/hosts/common/load-env.sh; load_dothomelab_env "$DOTHOMELAB_ENV"; exec /opt/dothomelab/hosts/infra/n8n/configure-owner.py'
  run "$repo_root/scripts/deploy-compose.sh" 110 \
    hosts/infra/pulse/compose.yaml
  run "$repo_root/hosts/infra/pulse/configure-monitoring.py"
  guest_exec 110 docker compose \
    -f /opt/dothomelab/hosts/infra/obsidian-sync/compose.yaml \
    --profile proton \
    build proton-drive
  run "$repo_root/scripts/deploy-compose.sh" 102 \
    hosts/servarr/hello/compose.yaml
  guest_exec 102 \
    /opt/dothomelab/hosts/servarr/shelfarr/configure-qbittorrent-internal-access.sh
  run "$repo_root/scripts/deploy-compose.sh" 102 \
    hosts/servarr/shelfarr/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/immich/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/audiobookshelf/compose.yaml
  run "$repo_root/scripts/initialize-shelfarr-audiobookshelf-env.py" \
    --env-file /root/.env
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/bar-assistant/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/bookorbit/compose.yaml
  guest_exec_with_env 112 \
    bash -lc \
    'source /opt/dothomelab/hosts/common/load-env.sh; load_dothomelab_env "$DOTHOMELAB_ENV"; exec /opt/dothomelab/hosts/apps/bookorbit/configure.py'
  guest_exec_with_env 102 \
    /opt/dothomelab/hosts/servarr/shelfarr/configure.sh
  guest_exec_with_env 112 \
    /opt/dothomelab/hosts/apps/storyteller/render-secret.sh
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/storyteller/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/slskd/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/droppedneedle/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/immichframe/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/kavita/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/loki/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/media/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/mealie/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/paperless-ngx/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/paperless-gpt/compose.yaml
  guest_exec_with_env 112 \
    bash -lc \
    'source /opt/dothomelab/hosts/common/load-env.sh; load_dothomelab_env "$DOTHOMELAB_ENV"; exec /opt/dothomelab/hosts/apps/paperless-gpt/configure-api-token.sh'
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/prometheus/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/services/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/snapotter/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/stirling-pdf/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/zotero-webdav/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/wizarr/compose.yaml
  run "$repo_root/scripts/deploy-compose.sh" 112 \
    hosts/apps/yt-dlp-web-ui/compose.yaml
  guest_exec 110 \
    /opt/dothomelab/hosts/infra/proxy/apply-consolidated-routes.sh
  guest_exec 110 \
    /opt/dothomelab/hosts/infra/proxy/apply-haos-route.sh
  guest_exec 110 \
    /opt/dothomelab/hosts/infra/homarr/apply-managed-apps.sh
  run "$repo_root/scripts/deploy-compose.sh" 110 \
    hosts/infra/wud/compose.yaml

  guest_exec 110 install -m 0755 \
    /opt/dothomelab/hosts/infra/wud/run-updates.py \
    /usr/local/sbin/dothomelab-wud-runner
  guest_exec 110 \
    /opt/dothomelab/hosts/infra/obsidian-sync/install-systemd.sh
  run "$repo_root/backup/proton/install.sh"
}

set_final_resolvers() {
  local ctid
  for ctid in 102 112 113; do
    if [[ "${CT_CREATED[$ctid]:-false}" == "true" ]]; then
      run pct set "$ctid" --nameserver "$PIHOLE_IP"
    fi
  done
}

main() {
  umask 077
  preflight
  install_host_prerequisites
  load_recovery_environment
  provision_storage

  ensure_template "$DEBIAN_13_TEMPLATE" 13
  DEBIAN13_REF="$ENSURED_TEMPLATE"
  create_guest 113 "$DEBIAN13_REF"
  provision_pbs_guest
  install_host_backup
  restore_latest_appdata
  require_recovered_appdata
  restore_haos_vm
  restore_pbs_admin_credential
  prepare_media_contract

  ensure_template "$DEBIAN_12_TEMPLATE" 12
  DEBIAN12_REF="$ENSURED_TEMPLATE"
  provision_application_guests
  install_docker_api_tls
  prepare_native_and_storage
  deploy_projects
  set_final_resolvers
  run "$repo_root/scripts/capture-native-recovery.sh"

  if ! "$skip_verify"; then
    run "$repo_root/provision/verify.sh"
  fi

  enable_host_backup_timer
  log "Bootstrap complete. Managed HAOS VM state was retained or restored; no router configuration was changed."
}

main
