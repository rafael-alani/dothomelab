#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

state_root="${PROTON_STATE_ROOT:-/state}"
shared_work_root="${PROTON_SHARED_WORK_ROOT:-/work}"
volatile_work_root="${PROTON_VOLATILE_WORK_ROOT:-/volatile-work}"
remote_root="${PROTON_BACKUP_REMOTE_ROOT:-/my-files/Backups/dothomelab}"
chunk_size="${PROTON_BACKUP_CHUNK_SIZE:-4096M}"

obsidian_source="${PROTON_SOURCE_OBSIDIAN:-/vault/shared/media/obsidian}"
photos_source="${PROTON_SOURCE_PHOTOS:-/vault/shared/media/photos}"
environment_source="${PROTON_SOURCE_ENVIRONMENT:-/sources/environment}"

current_cycle_file="$state_root/current-cycle"
last_cycle_epoch_file="$state_root/last-cycle.epoch"
last_cycle_at_file="$state_root/last-cycle.at"
last_cycle_id_file="$state_root/last-cycle.id"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

validate_cycle() {
  [[ "$1" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] ||
    die "Invalid cycle ID: $1"
}

validate_dataset() {
  case "$1" in
    obsidian | photos | environment) ;;
    *) die "Unknown backup dataset: $1" ;;
  esac
}

validate_remote_path() {
  local path="$1"
  local component
  [[ "$path" == /my-files/* ]] ||
    die "Proton backup paths must be below /my-files"
  [[ "$path" != *"//"* ]] ||
    die "Proton backup paths must not contain empty components"
  IFS=/ read -r -a components <<<"${path#/}"
  for component in "${components[@]}"; do
    [[ "$component" != "." && "$component" != ".." ]] ||
      die "Proton backup paths must not contain dot components"
  done
}

validate_configuration() {
  validate_remote_path "$remote_root"
  [[ "$chunk_size" =~ ^[1-9][0-9]*([KMGTP]i?B?|[kmgpt])?$ ]] ||
    die "Invalid PROTON_BACKUP_CHUNK_SIZE: $chunk_size"
  command -v cmp >/dev/null || die "cmp is required"
  command -v jq >/dev/null || die "jq is required"
  command -v sha256sum >/dev/null || die "sha256sum is required"
  command -v split >/dev/null || die "split is required"
  command -v tar >/dev/null || die "tar is required"
}

select_dataset() {
  dataset="$1"
  validate_dataset "$dataset"

  case "$dataset" in
    obsidian)
      source_root="$obsidian_source"
      work_root="$shared_work_root"
      remote_dir="$remote_root/Obsidian"
      archive_type="tar.gz"
      restore_owner_policy="preserve-numeric"
      ;;
    photos)
      source_root="$photos_source"
      work_root="$shared_work_root"
      remote_dir="$remote_root/Photos"
      archive_type="tar"
      restore_owner_policy="preserve-numeric"
      ;;
    environment)
      source_root="$environment_source"
      work_root="$volatile_work_root"
      remote_dir="$remote_root/Environment"
      archive_type="tar.gz"
      restore_owner_policy="root:root"
      ;;
  esac

  validate_remote_path "$remote_dir"
  dataset_state="$state_root/sources/$dataset"
  stage_root="$work_root/staging/$dataset"
  verify_root="$work_root/verify/$dataset"
  restore_root="$work_root/restore/$dataset"
  pending_file="$stage_root/pending"
}

generation_name_for() {
  local selected_dataset="$1"
  local cycle="$2"
  printf '%s-%s\n' "$selected_dataset" "$cycle"
}

validate_generation_name() {
  local selected_dataset="$1"
  local generation="$2"
  [[ "$generation" =~ ^${selected_dataset}-[0-9]{8}T[0-9]{6}Z$ ]] ||
    die "Invalid $selected_dataset generation name: $generation"
}

ensure_remote_directory() {
  local target="$1"
  local current=/my-files
  local remainder="${target#/my-files/}"
  local part
  local -a parts

  validate_remote_path "$target"
  IFS=/ read -r -a parts <<<"$remainder"
  for part in "${parts[@]}"; do
    [[ -n "$part" ]] || continue
    if ! proton-drive filesystem info "$current/$part" >/dev/null 2>&1; then
      proton-drive filesystem create-folder "$current" "$part" >/dev/null
    fi
    current="$current/$part"
  done
}

list_remote_generations() {
  local listing_json
  local generation_pattern
  generation_pattern="^${dataset}-[0-9]{8}T[0-9]{6}Z$"

  listing_json="$(
    proton-drive filesystem list -j -t folder "$remote_dir"
  )"

  if jq -e '
      .. | objects |
      select(
        has("uid") and
        (.name? | type == "object") and
        (.name.ok? == false)
      )
    ' >/dev/null <<<"$listing_json"; then
    die "A remote node name in $remote_dir could not be decrypted; retention is unsafe"
  fi

  jq -r --arg pattern "$generation_pattern" '
    .. | objects |
    select(has("uid") and has("name")) |
    (
      .name |
      if type == "object" then
        if .ok == true then .value else empty end
      elif type == "string" then
        .
      else
        empty
      end
    ) as $name |
    select(($name | type) == "string") |
    select($name | test($pattern)) |
    select((.uid | type) == "string") |
    [$name, .uid] |
    @tsv
  ' <<<"$listing_json" |
    sort -t $'\t' -k1,1
}

json_contains_uid() {
  local uid="$1"
  jq -e --arg uid "$uid" '
    .. | objects | select(.uid? == $uid)
  ' >/dev/null
}

list_scoped_trashed_generations() {
  local listing_json
  local generation_pattern
  generation_pattern="^${dataset}-[0-9]{8}T[0-9]{6}Z$"
  listing_json="$(proton-drive filesystem list -j /trash)"

  jq -r --arg pattern "$generation_pattern" '
    .. | objects |
    select(has("uid") and has("name")) |
    (
      .name |
      if type == "object" then
        if .ok == true then .value else empty end
      elif type == "string" then
        .
      else
        empty
      end
    ) as $name |
    select(($name | type) == "string") |
    select($name | test($pattern)) |
    select((.uid | type) == "string") |
    [$name, .uid] |
    @tsv
  ' <<<"$listing_json" |
    sort -t $'\t' -k1,1
}

delete_trashed_generation() {
  local generation="$1"
  local uid="$2"
  local attempt
  local trash_json
  local seen=false

  validate_generation_name "$dataset" "$generation"
  [[ "$uid" =~ ^[A-Za-z0-9_-]+$ ]] ||
    die "Refusing an invalid Proton trash node UID for $generation"

  for ((attempt = 1; attempt <= 10; attempt++)); do
    trash_json="$(proton-drive filesystem list -j /trash)"
    if json_contains_uid "$uid" <<<"$trash_json"; then
      seen=true
      proton-drive filesystem delete "/trash/$uid" >/dev/null 2>&1 || true
      trash_json="$(proton-drive filesystem list -j /trash)"
      if ! json_contains_uid "$uid" <<<"$trash_json"; then
        return 0
      fi
    elif [[ "$seen" == true ]]; then
      return 0
    fi
    sleep 2
  done
  die "$generation is still present in Proton trash after permanent deletion"
}

purge_scoped_generation_trash() {
  local listing
  local record
  local name
  local uid

  listing="$(list_scoped_trashed_generations)"
  [[ -n "$listing" ]] || return 0
  while IFS= read -r record; do
    [[ -n "$record" ]] || continue
    IFS=$'\t' read -r name uid <<<"$record"
    log "Finishing permanent deletion of previously trashed $dataset generation $name"
    delete_trashed_generation "$name" "$uid"
  done <<<"$listing"
}

delete_remote_generation() {
  local generation="$1"
  local uid="$2"

  validate_generation_name "$dataset" "$generation"
  [[ "$uid" =~ ^[A-Za-z0-9_-]+$ ]] ||
    die "Refusing an invalid Proton node UID for $generation"

  log "Permanently deleting oldest retained $dataset generation $generation"
  proton-drive filesystem trash "$remote_dir/$uid" >/dev/null
  delete_trashed_generation "$generation" "$uid"
}

prune_before_upload() {
  local generation="$1"
  local listing
  local record
  local name
  local uid
  local current_present=false
  local delete_count
  local -a entries=()
  local -a others=()

  purge_scoped_generation_trash
  listing="$(list_remote_generations)"
  if [[ -n "$listing" ]]; then
    mapfile -t entries <<<"$listing"
  fi

  for record in "${entries[@]}"; do
    IFS=$'\t' read -r name uid <<<"$record"
    validate_generation_name "$dataset" "$name"
    [[ "$uid" =~ ^[A-Za-z0-9_-]+$ ]] ||
      die "Remote generation $name has an invalid node UID"
    if [[ "$name" == "$generation" ]]; then
      current_present=true
    else
      others+=("$record")
    fi
  done

  if [[ "$current_present" == true ]]; then
    delete_count=$((${#others[@]} - 1))
  else
    delete_count=$((${#entries[@]} - 1))
  fi
  ((delete_count > 0)) || return 0

  for ((index = 0; index < delete_count; index++)); do
    record="${others[$index]:-${entries[$index]}}"
    IFS=$'\t' read -r name uid <<<"$record"
    delete_remote_generation "$name" "$uid"
  done
}

require_source_data() {
  [[ -d "$source_root" ]] ||
    die "Missing $dataset source directory: $source_root"

  case "$dataset" in
    obsidian)
      [[ -d "$source_root/.stfolder" ]] ||
        die "Syncthing has not initialized the Obsidian vault marker"
      find "$source_root" -mindepth 1 \
        ! -path "$source_root/.stfolder" \
        ! -path "$source_root/.stfolder/*" \
        -print -quit |
        grep -q . ||
        die "The Obsidian vault contains no user data"
      ;;
    photos)
      find "$source_root" -mindepth 1 -print -quit |
        grep -q . ||
        die "The photos directory contains no data"
      ;;
    environment)
      [[ -f "$source_root/root.env" && ! -L "$source_root/root.env" ]] ||
        die "The staged /root/.env copy is missing or is not a regular file"
      [[ "$(stat -c %a "$source_root/root.env")" == "600" ]] ||
        die "The staged /root/.env copy must have mode 0600"
      ;;
  esac
}

require_stage_capacity() {
  local source_bytes
  local available_bytes
  local fixed_headroom
  local required_bytes

  source_bytes="$(du -sbx "$source_root" | awk '{print $1}')"
  available_bytes="$(
    df -P -B1 "$work_root" |
      awk 'NR == 2 {print $4}'
  )"
  [[ "$source_bytes" =~ ^[0-9]+$ && "$available_bytes" =~ ^[0-9]+$ ]] ||
    die "Could not determine $dataset staging capacity"

  if [[ "$dataset" == "photos" ]]; then
    fixed_headroom=$((1024 * 1024 * 1024))
  else
    fixed_headroom=$((64 * 1024 * 1024))
  fi
  required_bytes=$((source_bytes + source_bytes / 20 + fixed_headroom))
  ((available_bytes >= required_bytes)) ||
    die "$dataset staging needs $required_bytes bytes including headroom; $work_root has $available_bytes"
}

write_manifest() {
  local destination="$1"
  local cycle="$2"
  cat >"$destination" <<EOF
format=dothomelab-proton-generation-v1
dataset=$dataset
cycle=$cycle
created_utc=$(date --utc --iso-8601=seconds)
archive_type=$archive_type
chunk_size=$chunk_size
restore_owner_policy=$restore_owner_policy
EOF
}

create_archive_parts() {
  local build_dir="$1"
  local -a tar_args=(
    --one-file-system
    --sort=name
    --format=pax
    "--pax-option=delete=atime,delete=ctime"
    --numeric-owner
  )

  case "$dataset" in
    obsidian)
      tar_args+=(
        --exclude=./.stfolder
        --exclude=./.stfolder/\*
        --exclude=*/.~syncthing~*.tmp
      )
      ;;
    environment)
      tar_args+=(--owner=0 --group=0)
      ;;
  esac

  if [[ "$archive_type" == "tar.gz" ]]; then
    tar "${tar_args[@]}" -C "$source_root" -cf - . |
      gzip -n -6 |
      split \
        --bytes="$chunk_size" \
        --numeric-suffixes=0 \
        --suffix-length=5 \
        - \
        "$build_dir/archive.tar.gz.part-"
  else
    tar "${tar_args[@]}" -C "$source_root" -cf - . |
      split \
        --bytes="$chunk_size" \
        --numeric-suffixes=0 \
        --suffix-length=5 \
        - \
        "$build_dir/archive.tar.part-"
  fi
}

verify_local_generation() {
  local generation_dir="$1"
  local expected_prefix
  [[ -f "$generation_dir/MANIFEST" ]] ||
    die "Missing generation manifest in $generation_dir"
  [[ -s "$generation_dir/SHA256SUMS" ]] ||
    die "Missing generation checksums in $generation_dir"

  if [[ "$archive_type" == "tar.gz" ]]; then
    expected_prefix="archive.tar.gz.part-"
  else
    expected_prefix="archive.tar.part-"
  fi

  while read -r expected_hash filename; do
    [[ "$expected_hash" =~ ^[0-9a-f]{64}$ ]] ||
      die "Invalid checksum entry in $generation_dir/SHA256SUMS"
    [[ "$filename" =~ ^${expected_prefix}[0-9]{5}$ ]] ||
      die "Invalid archive part name in $generation_dir/SHA256SUMS: $filename"
    [[ -f "$generation_dir/$filename" && ! -L "$generation_dir/$filename" ]] ||
      die "Missing or unsafe archive part: $generation_dir/$filename"
  done <"$generation_dir/SHA256SUMS"

  (
    cd "$generation_dir"
    sha256sum --check --strict SHA256SUMS >/dev/null
  )

  if [[ "$archive_type" == "tar.gz" ]]; then
    cat "$generation_dir"/archive.tar.gz.part-* | gzip -t
  fi
}

read_pending_generation() {
  [[ -s "$pending_file" ]] ||
    die "No staged $dataset generation is pending"
  pending_generation="$(tr -d '\n' <"$pending_file")"
  validate_generation_name "$dataset" "$pending_generation"
  [[ -d "$stage_root/$pending_generation" ]] ||
    die "Pending $dataset generation directory is missing"
}

dataset_completed_cycle() {
  local cycle="$1"
  [[ -s "$dataset_state/last-success.cycle" ]] &&
    [[ "$(<"$dataset_state/last-success.cycle")" == "$cycle" ]]
}

stage_generation() {
  local cycle="$1"
  local generation
  local build_dir
  local final_dir
  local pending_temp

  validate_cycle "$cycle"
  generation="$(generation_name_for "$dataset" "$cycle")"
  validate_generation_name "$dataset" "$generation"

  if dataset_completed_cycle "$cycle"; then
    log "Skipping $dataset staging: cycle $cycle is already verified"
    return 0
  fi

  install -d -m 0700 "$stage_root" "$verify_root" "$restore_root"
  if [[ -s "$pending_file" ]]; then
    read_pending_generation
    [[ "$pending_generation" == "$generation" ]] ||
      die "$dataset has pending generation $pending_generation, expected $generation"
    verify_local_generation "$stage_root/$pending_generation"
    log "Reusing staged $dataset generation $pending_generation"
    return 0
  fi

  require_source_data
  require_stage_capacity

  build_dir="$stage_root/.building-$generation"
  final_dir="$stage_root/$generation"
  [[ ! -e "$final_dir" ]] ||
    die "Untracked staged generation already exists: $final_dir"
  rm -rf -- "$build_dir"
  install -d -m 0700 "$build_dir"

  log "Staging $dataset generation $generation"
  create_archive_parts "$build_dir"
  write_manifest "$build_dir/MANIFEST" "$cycle"
  (
    cd "$build_dir"
    sha256sum archive.*.part-* >SHA256SUMS
  )
  verify_local_generation "$build_dir"

  mv "$build_dir" "$final_dir"
  pending_temp="$stage_root/.pending.$$"
  printf '%s\n' "$generation" >"$pending_temp"
  mv "$pending_temp" "$pending_file"
  log "Staged $dataset generation $generation ($(du -sh "$final_dir" | awk '{print $1}'))"
}

download_and_verify_remote_generation() {
  local generation="$1"
  local local_dir="$2"
  local verification_dir="$verify_root/$generation"
  local expected_hash
  local filename
  local downloaded_hash

  rm -rf -- "$verification_dir"
  install -d -m 0700 "$verification_dir"

  proton-drive filesystem download \
    --conflict-strategy replace \
    "$remote_dir/$generation/MANIFEST" \
    "$verification_dir" >/dev/null
  proton-drive filesystem download \
    --conflict-strategy replace \
    "$remote_dir/$generation/SHA256SUMS" \
    "$verification_dir" >/dev/null

  cmp "$local_dir/MANIFEST" "$verification_dir/MANIFEST" >/dev/null ||
    die "Remote manifest mismatch for $generation"
  cmp "$local_dir/SHA256SUMS" "$verification_dir/SHA256SUMS" >/dev/null ||
    die "Remote checksum manifest mismatch for $generation"

  while read -r expected_hash filename; do
    [[ "$expected_hash" =~ ^[0-9a-f]{64}$ ]] ||
      die "Invalid local checksum while verifying $generation"
    [[ "$filename" != */* && "$filename" != "." && "$filename" != ".." ]] ||
      die "Unsafe archive part name while verifying $generation"

    proton-drive filesystem download \
      --conflict-strategy replace \
      "$remote_dir/$generation/$filename" \
      "$verification_dir" >/dev/null
    downloaded_hash="$(
      sha256sum "$verification_dir/$filename" |
        awk '{print $1}'
    )"
    [[ "$downloaded_hash" == "$expected_hash" ]] ||
      die "Remote checksum mismatch for $generation/$filename"
    rm -f -- "$verification_dir/$filename"
  done <"$local_dir/SHA256SUMS"

  rm -rf -- "$verification_dir"
}

verify_remote_retention() {
  local generation="$1"
  local listing
  local record
  local name
  local count=0
  local current_found=false

  listing="$(list_remote_generations)"
  if [[ -n "$listing" ]]; then
    while IFS= read -r record; do
      [[ -n "$record" ]] || continue
      IFS=$'\t' read -r name _ <<<"$record"
      count=$((count + 1))
      [[ "$name" == "$generation" ]] && current_found=true
    done <<<"$listing"
  fi

  [[ "$current_found" == true ]] ||
    die "Uploaded generation $generation is not listed in $remote_dir"
  ((count <= 2)) ||
    die "$remote_dir retains $count generations; expected at most two"
}

record_dataset_success() {
  local cycle="$1"
  local generation="$2"
  local local_dir="$3"
  local manifest_hash

  manifest_hash="$(
    sha256sum "$local_dir/SHA256SUMS" |
      awk '{print $1}'
  )"
  install -d -m 0700 "$dataset_state"
  printf '%s\n' "$cycle" >"$dataset_state/last-success.cycle"
  printf '%s\n' "$generation" >"$dataset_state/last-success.name"
  printf '%s\n' "$manifest_hash" >"$dataset_state/last-success.manifest-sha256"
  date --utc --iso-8601=seconds >"$dataset_state/last-success.at"
}

upload_generation() {
  local cycle="$1"
  local generation
  local local_dir

  validate_cycle "$cycle"
  if dataset_completed_cycle "$cycle"; then
    log "Skipping $dataset upload: cycle $cycle is already verified"
    return 0
  fi

  read_pending_generation
  generation="$pending_generation"
  [[ "$generation" == "$(generation_name_for "$dataset" "$cycle")" ]] ||
    die "Pending $dataset generation $generation does not match cycle $cycle"
  local_dir="$stage_root/$generation"
  verify_local_generation "$local_dir"

  ensure_remote_directory "$remote_dir"
  prune_before_upload "$generation"

  log "Uploading $dataset generation $generation to $remote_dir"
  proton-drive filesystem upload \
    --file-conflict-strategy replace \
    --folder-conflict-strategy merge \
    --skip-thumbnails \
    "$local_dir" \
    "$remote_dir" >/dev/null
  proton-drive filesystem info "$remote_dir/$generation" >/dev/null

  download_and_verify_remote_generation "$generation" "$local_dir"
  verify_remote_retention "$generation"
  record_dataset_success "$cycle" "$generation" "$local_dir"

  rm -rf -- "$local_dir"
  rm -f -- "$pending_file"
  log "Uploaded and checksum-verified $dataset generation $generation"
}

begin_cycle() {
  local cycle="$1"
  validate_cycle "$cycle"
  install -d -m 0700 "$state_root" "$state_root/sources"

  if [[ -s "$current_cycle_file" ]]; then
    [[ "$(<"$current_cycle_file")" == "$cycle" ]] ||
      die "Backup cycle $(<"$current_cycle_file") is incomplete; refusing cycle $cycle"
  else
    printf '%s\n' "$cycle" >"$current_cycle_file"
  fi
}

complete_cycle() {
  local cycle="$1"
  local selected
  local cycle_file
  local epoch_temp
  local at_temp

  validate_cycle "$cycle"
  [[ -s "$current_cycle_file" && "$(<"$current_cycle_file")" == "$cycle" ]] ||
    die "Cycle $cycle is not the active backup cycle"

  for selected in obsidian photos environment; do
    cycle_file="$state_root/sources/$selected/last-success.cycle"
    [[ -s "$cycle_file" && "$(<"$cycle_file")" == "$cycle" ]] ||
      die "$selected has not completed backup cycle $cycle"
  done

  epoch_temp="$state_root/.last-cycle.epoch.$$"
  at_temp="$state_root/.last-cycle.at.$$"
  date +%s >"$epoch_temp"
  date --utc --iso-8601=seconds >"$at_temp"
  mv "$epoch_temp" "$last_cycle_epoch_file"
  mv "$at_temp" "$last_cycle_at_file"
  printf '%s\n' "$cycle" >"$last_cycle_id_file"
  rm -f -- "$current_cycle_file"
  log "Completed all Proton backups for cycle $cycle"
}

restore_generation() {
  local selected_dataset="$1"
  local generation="$2"
  local destination

  select_dataset "$selected_dataset"
  validate_generation_name "$dataset" "$generation"
  proton-drive filesystem info "$remote_dir/$generation" >/dev/null
  install -d -m 0700 "$restore_root"
  destination="$restore_root/$generation"
  [[ ! -e "$destination" ]] ||
    die "Restore destination already exists: $destination"

  proton-drive filesystem download \
    "$remote_dir/$generation" \
    "$restore_root" >/dev/null
  [[ -d "$destination" ]] ||
    die "Proton did not create the expected restore directory: $destination"
  verify_local_generation "$destination"
  log "Downloaded and checksum-verified $generation to $destination; it has not been extracted"
}

status() {
  local selected
  local selected_state

  if [[ -s "$current_cycle_file" ]]; then
    printf 'Incomplete cycle: %s\n' "$(<"$current_cycle_file")"
  else
    printf 'Incomplete cycle: none\n'
  fi
  if [[ -s "$last_cycle_at_file" ]]; then
    printf 'Last complete cycle: %s\n' "$(<"$last_cycle_at_file")"
  else
    printf 'Last complete cycle: none\n'
  fi

  for selected in obsidian photos environment; do
    selected_state="$state_root/sources/$selected"
    if [[ -s "$selected_state/last-success.name" ]] &&
      [[ -s "$selected_state/last-success.at" ]]; then
      printf '%s: %s at %s\n' \
        "$selected" \
        "$(<"$selected_state/last-success.name")" \
        "$(<"$selected_state/last-success.at")"
    else
      printf '%s: no checksum-verified generation\n' "$selected"
    fi
  done
}

validate_configuration

case "${1:-}" in
  begin-cycle)
    [[ $# -eq 2 ]] || die "Usage: proton-backup begin-cycle <cycle-id>"
    begin_cycle "$2"
    ;;
  stage)
    [[ $# -eq 3 ]] || die "Usage: proton-backup stage <dataset> <cycle-id>"
    select_dataset "$2"
    stage_generation "$3"
    ;;
  upload)
    [[ $# -eq 3 ]] || die "Usage: proton-backup upload <dataset> <cycle-id>"
    select_dataset "$2"
    upload_generation "$3"
    ;;
  complete-cycle)
    [[ $# -eq 2 ]] || die "Usage: proton-backup complete-cycle <cycle-id>"
    complete_cycle "$2"
    ;;
  restore)
    [[ $# -eq 3 ]] || die "Usage: proton-backup restore <dataset> <generation>"
    restore_generation "$2" "$3"
    ;;
  status)
    [[ $# -eq 1 ]] || die "Usage: proton-backup status"
    status
    ;;
  *)
    printf '%s\n' \
      'Usage: proton-backup {' \
      '  begin-cycle <cycle-id> |' \
      '  stage <obsidian|photos|environment> <cycle-id> |' \
      '  upload <obsidian|photos|environment> <cycle-id> |' \
      '  complete-cycle <cycle-id> |' \
      '  restore <obsidian|photos|environment> <generation> |' \
      '  status' \
      '}' >&2
    exit 2
    ;;
esac
