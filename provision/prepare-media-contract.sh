#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/inventory.env"

dry_run=false

usage() {
  cat <<'EOF'
Usage: ./provision/prepare-media-contract.sh [--dry-run]

Create only missing exact media-contract directories on the Proxmox host.
Existing directories, ownership, modes, ACLs, and contents are never changed.
EOF
}

while (($#)); do
  case "$1" in
    --dry-run)
      dry_run=true
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

print_command() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
}

require_dataset_mount() {
  local dataset="$1"
  local target="$2"
  local source

  [[ -d "$target" ]] || fail "canonical dataset mount is missing: $target"
  source="$(findmnt -rn -o SOURCE -T "$target")"
  [[ "$source" == "$dataset" ]] ||
    fail "$target is backed by $source, expected $dataset"
}

ensure_exact_directory() {
  local path="$1"
  local uid="$2"
  local gid="$3"
  local mode="$4"

  if [[ -e "$path" ]]; then
    [[ -d "$path" && ! -L "$path" ]] ||
      fail "contract path exists but is not a physical directory: $path"
    printf 'KEEP %s\n' "$path"
    return 0
  fi

  if "$dry_run"; then
    print_command install -d -o "$uid" -g "$gid" -m "$mode" "$path"
  else
    install -d -o "$uid" -g "$gid" -m "$mode" "$path"
    printf 'CREATE %s\n' "$path"
  fi
}

main() {
  [[ $EUID -eq 0 ]] || fail "run as root on the Proxmox host"
  for command_name in findmnt install; do
    command -v "$command_name" >/dev/null ||
      fail "required command is missing: $command_name"
  done

  "$script_dir/verify-media-contract.sh" --repository
  require_dataset_mount "$SHARED_DATASET" "$SHARED_MOUNT"
  require_dataset_mount "$APPDATA_DATASET" "$APPDATA_MOUNT"

  local path
  for path in "${MEDIA_CONTRACT_SHARED_PATHS[@]}"; do
    ensure_exact_directory \
      "$path" \
      "$MEDIA_CONTRACT_SHARED_UID" \
      "$MEDIA_CONTRACT_SHARED_GID" \
      "$MEDIA_CONTRACT_SHARED_MODE"
  done
  for path in "${MEDIA_CONTRACT_APPDATA_PATHS[@]}"; do
    ensure_exact_directory \
      "$path" \
      "$MEDIA_CONTRACT_APPDATA_UID" \
      "$MEDIA_CONTRACT_APPDATA_GID" \
      "$MEDIA_CONTRACT_APPDATA_MODE"
  done

  if "$dry_run"; then
    printf 'DRY-RUN media-contract directory reconciliation complete\n'
  else
    "$script_dir/verify-media-contract.sh" --host
  fi
}

main
