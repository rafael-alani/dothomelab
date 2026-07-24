#!/usr/bin/env bash
set -euo pipefail

umask 077

state_root=/state
source_root=/source
remote_dir="${PROTON_BACKUP_REMOTE_DIR:-/my-files/Backups/Obsidian}"
staging_dir="$state_root/staging"
pending_file="$staging_dir/pending.env"
last_hash_file="$state_root/last-success.sha256"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

ensure_remote_directory() {
  if [[ "$remote_dir" != /my-files/* ]] || [[ "$remote_dir" == *"//"* ]]; then
    log "PROTON_BACKUP_REMOTE_DIR must be below /my-files"
    return 1
  fi

  local current=/my-files
  local remainder="${remote_dir#/my-files/}"
  local part
  IFS=/ read -r -a parts <<<"$remainder"

  for part in "${parts[@]}"; do
    [[ -n "$part" ]] || continue
    if ! proton-drive filesystem info "$current/$part" >/dev/null 2>&1; then
      proton-drive filesystem create-folder "$current" "$part" >/dev/null
    fi
    current="$current/$part"
  done
}

stage_archive() {
  mkdir -p "$staging_dir"

  if [[ -s "$pending_file" ]]; then
    log "A previously staged archive is still pending; it will be retried"
    return 0
  fi

  if [[ ! -d "$source_root/.stfolder" ]]; then
    log "Skipping: Syncthing has not initialized the vault marker"
    return 0
  fi

  if ! find "$source_root" -mindepth 1 \
      ! -path "$source_root/.stfolder" \
      ! -path "$source_root/.stfolder/*" \
      -print -quit | grep -q .; then
    log "Skipping: the vault contains no user data"
    return 0
  fi

  local temporary_tar="$staging_dir/obsidian-vault.pending.tar"
  local temporary_archive="${temporary_tar}.gz"
  rm -f "$temporary_tar" "$temporary_archive"

  tar \
    --one-file-system \
    --sort=name \
    --format=pax \
    --pax-option=delete=atime,delete=ctime \
    --numeric-owner \
    --owner=0 \
    --group=0 \
    --exclude='./.stfolder' \
    --exclude='./.stfolder/*' \
    --exclude='*/.~syncthing~*.tmp' \
    -C "$source_root" \
    -cf "$temporary_tar" .
  gzip -n -9 "$temporary_tar"

  local archive_hash
  archive_hash="$(sha256sum "$temporary_archive" | awk '{print $1}')"

  if [[ -s "$last_hash_file" ]] &&
     [[ "$(tr -d '[:space:]' <"$last_hash_file")" == "$archive_hash" ]]; then
    rm -f "$temporary_archive"
    log "Skipping: vault content and metadata are unchanged"
    return 0
  fi

  local timestamp
  local archive_name
  timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
  archive_name="obsidian-vault-${timestamp}-${archive_hash:0:12}.tar.gz"
  mv "$temporary_archive" "$staging_dir/$archive_name"

  {
    printf 'archive_name=%s\n' "$archive_name"
    printf 'archive_sha256=%s\n' "$archive_hash"
  } >"$pending_file"

  log "Staged $archive_name"
}

read_pending() {
  archive_name="$(sed -n 's/^archive_name=//p' "$pending_file")"
  archive_sha256="$(sed -n 's/^archive_sha256=//p' "$pending_file")"

  if [[ ! "$archive_name" =~ ^obsidian-vault-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}\.tar\.gz$ ]] ||
     [[ ! "$archive_sha256" =~ ^[0-9a-f]{64}$ ]] ||
     [[ ! -f "$staging_dir/$archive_name" ]]; then
    log "Pending backup metadata is invalid"
    return 1
  fi
}

upload_archive() {
  if [[ ! -s "$pending_file" ]]; then
    log "No new archive is pending"
    return 0
  fi

  local archive_name
  local archive_sha256
  read_pending
  ensure_remote_directory

  log "Uploading $archive_name to $remote_dir"
  proton-drive filesystem upload \
    --conflict-strategy skip \
    --skip-thumbnails \
    "$staging_dir/$archive_name" \
    "$remote_dir"

  proton-drive filesystem info "$remote_dir/$archive_name" >/dev/null

  local verify_dir="$state_root/verify/current"
  rm -rf "$verify_dir"
  mkdir -p "$verify_dir"
  proton-drive filesystem download \
    --conflict-strategy replace \
    "$remote_dir/$archive_name" \
    "$verify_dir"

  if [[ ! -f "$verify_dir/$archive_name" ]]; then
    log "Verification download did not produce the expected archive"
    return 1
  fi

  local downloaded_hash
  downloaded_hash="$(sha256sum "$verify_dir/$archive_name" | awk '{print $1}')"
  if [[ "$downloaded_hash" != "$archive_sha256" ]]; then
    log "Verification checksum mismatch for $archive_name"
    return 1
  fi
  gzip -t "$verify_dir/$archive_name"
  tar -tzf "$verify_dir/$archive_name" >/dev/null

  mkdir -p "$state_root/latest"
  mv "$staging_dir/$archive_name" "$state_root/latest/$archive_name"
  find "$state_root/latest" -maxdepth 1 -type f \
    -name 'obsidian-vault-*.tar.gz' \
    ! -name "$archive_name" -delete
  printf '%s\n' "$archive_sha256" >"$last_hash_file"
  printf '%s\n' "$archive_name" >"$state_root/last-success.name"
  date --utc --iso-8601=seconds >"$state_root/last-success-at"
  rm -f "$pending_file"
  rm -rf "$verify_dir"

  log "Uploaded and checksum-verified $archive_name"
}

restore_archive() {
  local archive_name="${1:-}"
  if [[ ! "$archive_name" =~ ^obsidian-vault-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}\.tar\.gz$ ]]; then
    printf 'Usage: proton-backup restore <archive-name>\n' >&2
    return 2
  fi

  mkdir -p "$state_root/restore"
  proton-drive filesystem download \
    --conflict-strategy replace \
    "$remote_dir/$archive_name" \
    "$state_root/restore"
  gzip -t "$state_root/restore/$archive_name"
  tar -tzf "$state_root/restore/$archive_name" >/dev/null
  sha256sum "$state_root/restore/$archive_name"
  log "Downloaded and archive-verified $archive_name to /state/restore"
}

status() {
  if [[ -s "$state_root/last-success.name" ]] &&
     [[ -s "$state_root/last-success-at" ]]; then
    printf 'Last verified backup: %s at %s\n' \
      "$(cat "$state_root/last-success.name")" \
      "$(cat "$state_root/last-success-at")"
  else
    printf 'No verified Proton backup has completed yet.\n'
  fi

  if [[ -s "$pending_file" ]]; then
    printf 'Pending retry: %s\n' "$(sed -n 's/^archive_name=//p' "$pending_file")"
  fi
}

case "${1:-}" in
  stage)
    stage_archive
    ;;
  upload)
    upload_archive
    ;;
  run)
    stage_archive
    upload_archive
    ;;
  restore)
    shift
    restore_archive "$@"
    ;;
  status)
    status
    ;;
  *)
    printf 'Usage: proton-backup {stage|upload|run|restore <archive-name>|status}\n' >&2
    exit 2
    ;;
esac
