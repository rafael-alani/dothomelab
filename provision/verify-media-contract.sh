#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly repo_root="$(cd -- "$script_dir/.." && pwd)"
# shellcheck disable=SC1091
source "$script_dir/inventory.env"

mode="repository"

usage() {
  cat <<'EOF'
Usage: ./provision/verify-media-contract.sh MODE

Modes:
  --repository  Validate declarations and documentation without live access.
  --host        Also validate host paths, datasets, ownership, and free space.
  --live        Also validate CT102/CT112 mounts and UID 1000 access.

No mode writes probe files or changes host, guest, media, or appdata state.
EOF
}

while (($#)); do
  case "$1" in
    --repository)
      mode="repository"
      ;;
    --host)
      mode="host"
      ;;
    --live)
      mode="live"
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

ok() {
  printf 'OK   %s\n' "$*"
}

require_literal() {
  local actual="$1"
  local expected="$2"
  local description="$3"
  [[ "$actual" == "$expected" ]] ||
    fail "$description is $actual, expected $expected"
}

require_paths_below() {
  local root="$1"
  shift
  local path
  local seen=""
  for path in "$@"; do
    [[ "$path" == "$root/"* ]] ||
      fail "contract path escapes $root: $path"
    case "
$seen
" in
      *"
$path
"*)
        fail "duplicate contract path: $path"
        ;;
    esac
    seen="${seen}${seen:+
}$path"
  done
}

verify_repository_contract() {
  require_literal "$MEDIA_EBOOKS_HOST_PATH" \
    "/vault/shared/media/books/ebooks" "ebook path"
  require_literal "$MEDIA_PDFS_HOST_PATH" \
    "/vault/shared/media/books/pdfs" "PDF path"
  require_literal "$MEDIA_COMICS_HOST_PATH" \
    "/vault/shared/media/comics" "comics path"
  require_literal "$MEDIA_MANGAS_HOST_PATH" \
    "/vault/shared/media/mangas" "mangas path"
  require_literal "$MEDIA_AUDIOBOOKS_HOST_PATH" \
    "/vault/shared/media/audiobooks" "audiobook path"
  require_literal "$PINEPODS_PODCASTS_HOST_PATH" \
    "/vault/shared/media/podcasts/pinepods" "PinePods path"
  require_literal "$MEDIA_MUSIC_HOST_PATH" \
    "/vault/shared/media/music" "music path"
  require_literal "$AURRAL_FLOWS_HOST_PATH" \
    "/vault/shared/media/aurral-flows" "Aurral flow path"
  require_literal "$STORYTELLER_INBOX_HOST_PATH" \
    "/vault/shared/media/storyteller/inbox" "Storyteller inbox path"
  require_literal "$STORYTELLER_LIBRARY_HOST_PATH" \
    "/vault/shared/media/storyteller/library" "Storyteller library path"
  require_literal "$SHELFARR_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/shelfarr" "Shelfarr appdata path"
  require_literal "$BOOKORBIT_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/bookorbit" "BookOrbit appdata path"
  require_literal "$AUDIOBOOKSHELF_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/audiobookshelf" "Audiobookshelf appdata path"
  require_literal "$STORYTELLER_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/storyteller" "Storyteller appdata path"
  require_literal "$PINEPODS_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/pinepods" "PinePods appdata path"
  require_literal "$AURRAL_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/aurral" "Aurral appdata path"
  require_literal "$SOULARR_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/soularr" "Soularr appdata path"
  require_literal "$NAVIDROME_APPDATA_HOST_PATH" \
    "/srv/appdata/docker/navidrome" "Navidrome appdata path"

  [[ "${#MEDIA_CONTRACT_SHARED_PATHS[@]}" == "13" ]] ||
    fail "expected 13 shared contract paths"
  [[ "${#MEDIA_CONTRACT_APPDATA_PATHS[@]}" == "8" ]] ||
    fail "expected 8 appdata contract paths"
  require_paths_below "$SHARED_MOUNT" "${MEDIA_CONTRACT_SHARED_PATHS[@]}"
  require_paths_below "$APPDATA_MOUNT" "${MEDIA_CONTRACT_APPDATA_PATHS[@]}"
  [[ "$MEDIA_CONTRACT_MIN_SHARED_FREE_GIB" =~ ^[1-9][0-9]*$ ]] ||
    fail "shared free-space floor is not a positive integer"
  [[ "$MEDIA_CONTRACT_MIN_APPDATA_FREE_GIB" =~ ^[1-9][0-9]*$ ]] ||
    fail "appdata free-space floor is not a positive integer"

  [[ -r "$repo_root/docs/media-data-contract.md" ]] ||
    fail "media data contract documentation is missing"
  grep -Fq 'ebooks/<book-key>/Book.epub' \
    "$repo_root/docs/media-data-contract.md" ||
    fail "ebook book-key result is not documented"
  grep -Fq 'audiobooks/<book-key>/Book.m4b' \
    "$repo_root/docs/media-data-contract.md" ||
    fail "audiobook book-key result is not documented"
  ok "repository declares the canonical media paths and shared book key"
}

dataset_source_for() {
  findmnt -rn -o SOURCE -T "$1"
}

require_dataset_path() {
  local path="$1"
  local dataset="$2"
  local uid="$3"
  local gid="$4"
  local mode_value="$5"
  local source

  [[ -d "$path" && ! -L "$path" ]] ||
    fail "contract directory is missing or is a symlink: $path"
  source="$(dataset_source_for "$path")"
  [[ "$source" == "$dataset" ]] ||
    fail "$path is backed by $source, expected $dataset"
  [[ "$(stat -c '%u' "$path")" == "$uid" ]] ||
    fail "$path has unexpected owner UID"
  [[ "$(stat -c '%g' "$path")" == "$gid" ]] ||
    fail "$path has unexpected owner GID"
  [[ "0$(stat -c '%a' "$path")" == "$mode_value" ]] ||
    fail "$path has unexpected mode"
}

require_free_space() {
  local dataset="$1"
  local minimum_gib="$2"
  local available_bytes
  local minimum_bytes

  available_bytes="$(zfs get -Hp -o value available "$dataset")"
  [[ "$available_bytes" =~ ^[0-9]+$ ]] ||
    fail "could not read available bytes for $dataset"
  minimum_bytes=$((minimum_gib * 1024 * 1024 * 1024))
  ((available_bytes >= minimum_bytes)) ||
    fail "$dataset has less than ${minimum_gib} GiB available"
  ok "$dataset free-space floor passed (${minimum_gib} GiB required)"
}

verify_host_contract() {
  [[ $EUID -eq 0 ]] || fail "host/live verification requires root"
  for command_name in findmnt stat zfs; do
    command -v "$command_name" >/dev/null ||
      fail "required command is missing: $command_name"
  done

  require_literal "$(zfs get -H -o value mountpoint "$SHARED_DATASET")" \
    "$SHARED_MOUNT" "$SHARED_DATASET mountpoint"
  require_literal "$(zfs get -H -o value mountpoint "$APPDATA_DATASET")" \
    "$APPDATA_MOUNT" "$APPDATA_DATASET mountpoint"

  local path
  for path in "${MEDIA_CONTRACT_SHARED_PATHS[@]}"; do
    require_dataset_path \
      "$path" \
      "$SHARED_DATASET" \
      "$MEDIA_CONTRACT_SHARED_UID" \
      "$MEDIA_CONTRACT_SHARED_GID" \
      "$MEDIA_CONTRACT_SHARED_MODE"
  done
  for path in "${MEDIA_CONTRACT_APPDATA_PATHS[@]}"; do
    require_dataset_path \
      "$path" \
      "$APPDATA_DATASET" \
      "$MEDIA_CONTRACT_APPDATA_UID" \
      "$MEDIA_CONTRACT_APPDATA_GID" \
      "$MEDIA_CONTRACT_APPDATA_MODE"
  done
  ok "all declared media and future appdata directories have expected metadata"

  require_free_space \
    "$SHARED_DATASET" "$MEDIA_CONTRACT_MIN_SHARED_FREE_GIB"
  require_free_space \
    "$APPDATA_DATASET" "$MEDIA_CONTRACT_MIN_APPDATA_FREE_GIB"
}

guest_path_from_host() {
  local host_path="$1"
  local host_root="$2"
  local guest_root="$3"
  printf '%s/%s\n' "$guest_root" "${host_path#"$host_root"/}"
}

guest_findmnt_field() {
  local ctid="$1"
  local field="$2"
  local path="$3"
  pct exec "$ctid" -- findmnt -rn -o "$field" -T "$path"
}

require_guest_mount() {
  local ctid="$1"
  local path="$2"
  local dataset="$3"
  local expected_mode="$4"
  local source
  local options
  local actual_mode

  source="$(guest_findmnt_field "$ctid" SOURCE "$path")"
  [[ "$source" == "$dataset"* ]] ||
    fail "CT$ctid $path is backed by $source, expected $dataset"
  options="$(guest_findmnt_field "$ctid" OPTIONS "$path")"
  case ",$options," in
    *,ro,*)
      actual_mode="ro"
      ;;
    *)
      actual_mode="rw"
      ;;
  esac
  [[ "$actual_mode" == "$expected_mode" ]] ||
    fail "CT$ctid $path is $actual_mode, expected $expected_mode"
}

require_guest_access() {
  local ctid="$1"
  local path="$2"
  local expected_mode="$3"

  pct exec "$ctid" -- test -d "$path" ||
    fail "CT$ctid path is missing: $path"
  pct exec "$ctid" -- setpriv \
    --reuid=1000 --regid=1000 --clear-groups test -r "$path" ||
    fail "CT$ctid UID/GID 1000 cannot read $path"

  if [[ "$expected_mode" == "rw" ]]; then
    pct exec "$ctid" -- setpriv \
      --reuid=1000 --regid=1000 --clear-groups test -w "$path" ||
      fail "CT$ctid UID/GID 1000 cannot write $path"
  elif pct exec "$ctid" -- setpriv \
    --reuid=1000 --regid=1000 --clear-groups test -w "$path"; then
    fail "CT$ctid UID/GID 1000 can write read-only contract path $path"
  fi
}

verify_live_contract() {
  for command_name in pct setpriv; do
    command -v "$command_name" >/dev/null ||
      fail "required command is missing: $command_name"
  done

  local config102
  local config112
  config102="$(pct config 102)"
  config112="$(pct config 112)"
  grep -Fqx "unprivileged: 1" <<<"$config102" ||
    fail "CT102 is not unprivileged"
  grep -Fqx "unprivileged: 1" <<<"$config112" ||
    fail "CT112 is not unprivileged"
  grep -Fqx "mp0: $SHARED_MOUNT,mp=/data" <<<"$config102" ||
    fail "CT102 shared read-write mount drifted"
  grep -Fqx "mp0: $SHARED_MOUNT,mp=/data,ro=1" <<<"$config112" ||
    fail "CT112 broad shared mount is not read-only"
  grep -Fqx \
    "mp3: $MEDIA_MUSIC_HOST_PATH,mp=$SLSKD_MUSIC_GUEST_PATH" \
    <<<"$config112" ||
    fail "CT112 existing narrow music mount drifted"
  grep -Fqx \
    "mp5: $MEDIA_PODCASTS_HOST_PATH,mp=$AUDIOBOOKSHELF_PODCASTS_GUEST_PATH" \
    <<<"$config112" ||
    fail "CT112 existing narrow podcast mount drifted"

  require_guest_mount 102 /data "$SHARED_DATASET" rw
  require_guest_mount 102 /docker "$APPDATA_DATASET" rw
  require_guest_mount 112 /data "$SHARED_DATASET" ro
  require_guest_mount 112 /srv/appdata/docker "$APPDATA_DATASET" rw
  require_guest_mount 112 /music "$SHARED_DATASET" rw
  require_guest_mount 112 /podcasts "$SHARED_DATASET" rw

  local host_path
  local guest_path
  for host_path in "${MEDIA_CONTRACT_SHARED_PATHS[@]}"; do
    guest_path="$(guest_path_from_host "$host_path" "$SHARED_MOUNT" /data)"
    require_guest_access 102 "$guest_path" rw
    require_guest_access 112 "$guest_path" ro
  done
  ok "CT102 UID/GID 1000 has RW and CT112 /data has RO canonical-media access"

  require_guest_access 112 /music rw
  require_guest_access 112 /podcasts rw
  require_guest_access 112 /podcasts/pinepods rw
  ok "CT112 existing narrow music and podcast mounts remain read-write"

  require_guest_access 102 /docker/shelfarr rw
  for host_path in \
    "$BOOKORBIT_APPDATA_HOST_PATH" \
    "$AUDIOBOOKSHELF_APPDATA_HOST_PATH" \
    "$STORYTELLER_APPDATA_HOST_PATH" \
    "$PINEPODS_APPDATA_HOST_PATH" \
    "$AURRAL_APPDATA_HOST_PATH" \
    "$SOULARR_APPDATA_HOST_PATH" \
    "$NAVIDROME_APPDATA_HOST_PATH"; do
    guest_path="$(guest_path_from_host \
      "$host_path" "$APPDATA_MOUNT" /srv/appdata/docker)"
    require_guest_access 112 "$guest_path" rw
  done
  ok "future service appdata is writable only through the existing appdata mounts"
}

main() {
  verify_repository_contract
  [[ "$mode" == "repository" ]] && return 0
  verify_host_contract
  [[ "$mode" == "host" ]] && return 0
  verify_live_contract
  printf '\nMedia data contract verification passed without write probes.\n'
}

main
