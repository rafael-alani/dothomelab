#!/usr/bin/env bash
set -Eeuo pipefail

: "${MOCK_PROTON_ROOT:?}"
: "${MOCK_PROTON_LOG:?}"

uid_for_name() {
  local digest
  digest="$(printf '%s' "$1" | sha256sum | cut -d' ' -f1)"
  printf '%086d==~%s%022d==' 0 "$digest" 0
}

map_path() {
  case "$1" in
    /my-files)
      printf '%s/my-files\n' "$MOCK_PROTON_ROOT"
      ;;
    /my-files/*)
      local mapped="$MOCK_PROTON_ROOT/my-files/${1#/my-files/}"
      local leaf="${mapped##*/}" child
      if [[ "$leaf" == *~* ]]; then
        for child in "${mapped%/*}"/*; do
          if [[ "$(uid_for_name "${child##*/}")" == "$leaf" ]]; then
            printf '%s\n' "$child"
            return 0
          fi
        done
        return 1
      fi
      printf '%s\n' "$mapped"
      ;;
    /trash)
      printf '%s/trash\n' "$MOCK_PROTON_ROOT"
      ;;
    /trash/*)
      printf '%s/trash/%s\n' "$MOCK_PROTON_ROOT" "${1#/trash/}"
      ;;
    *)
      echo "mock received unsupported path: $1" >&2
      exit 2
      ;;
  esac
}

log_operation() {
  printf '%s %s\n' "$1" "$2" >>"$MOCK_PROTON_LOG"
}

[[ "${1:-}" == "filesystem" ]] || {
  echo "mock supports only filesystem commands" >&2
  exit 2
}
shift
command_name="${1:-}"
shift

case "$command_name" in
  info)
    json=false
    if [[ "${1:-}" == -j ]]; then json=true; shift; fi
    local_path="$(map_path "$1")"
    [[ -e "$local_path" ]]
    if [[ "$json" == true ]]; then
      name="${local_path##*/}"
      revision="$(uid_for_name "$(sha256sum "$local_path"; stat -c %y "$local_path")")"
      jq -cn --arg uid "$(uid_for_name "$name")" --arg revision "$revision" \
        '{uid:$uid,type:"file",activeRevision:{ok:true,value:{uid:$revision}}}'
    fi
    ;;
  create-folder)
    parent="$(map_path "$1")"
    name="$2"
    [[ -d "$parent" ]]
    mkdir "$parent/$name"
    ;;
  list)
    if [[ "${MOCK_PROTON_FAIL_LIST_ONCE:-0}" == 1 && ! -e "$MOCK_PROTON_LOG.failed-list" ]]; then
      touch "$MOCK_PROTON_LOG.failed-list"
      exit 1
    fi
    folders_only=false
    while [[ "${1:-}" == -* ]]; do
      case "$1" in
        -j)
          shift
          ;;
        -t)
          folders_only=true
          shift 2
          ;;
        *)
          echo "mock received unsupported list option: $1" >&2
          exit 2
          ;;
      esac
    done
    target="$(map_path "$1")"
    [[ -d "$target" ]]
    first=true
    printf '['
    shopt -s nullglob
    for child in "$target"/*; do
      [[ "$folders_only" == false || -d "$child" ]] || continue
      name="$(basename "$child")"
      if [[ "$first" == true ]]; then
        first=false
      else
        printf ','
      fi
      jq -cn --arg name "$name" --arg uid "$(uid_for_name "$name")" \
        '{uid:$uid,type:"folder",name:{ok:true,value:$name}}'
    done
    shopt -u nullglob
    printf ']\n'
    ;;
  trash)
    source_path="$(map_path "$1")"
    name="$(basename "$source_path")"
    [[ -e "$source_path" ]]
    [[ ! -e "$MOCK_PROTON_ROOT/trash/$name" ]]
    log_operation trash "$name"
    mv "$source_path" "$MOCK_PROTON_ROOT/trash/$name"
    ;;
  delete)
    target="$(map_path "$1")"
    name="$(basename "$target")"
    [[ -e "$target" ]]
    log_operation delete "$name"
    rm -rf -- "$target"
    ;;
  upload)
    while (($# > 2)); do
      case "$1" in
        --file-conflict-strategy | --folder-conflict-strategy | --conflict-strategy)
          shift 2
          ;;
        --skip-thumbnails)
          shift
          ;;
        *)
          echo "mock received unsupported upload option: $1" >&2
          exit 2
          ;;
      esac
    done
    local_source="$1"
    parent="$(map_path "$2")"
    name="$(basename "$local_source")"
    [[ -d "$local_source" && -d "$parent" ]]
    log_operation upload "$name"
    rm -rf -- "${parent:?}/${name:?}"
    cp -a "$local_source" "$parent/$name"
    ;;
  download)
    while (($# > 2)); do
      case "$1" in
        --conflict-strategy)
          shift 2
          ;;
        *)
          echo "mock received unsupported download option: $1" >&2
          exit 2
          ;;
      esac
    done
    remote_source="$(map_path "$1")"
    local_parent="$2"
    name="$(basename "$remote_source")"
    [[ -e "$remote_source" && -d "$local_parent" ]]
    log_operation download "$name"
    if [[ "${MOCK_PROTON_FAIL_DOWNLOAD:-}" == "$name" ]]; then exit 1; fi
    if [[ "${MOCK_PROTON_FAIL_ONCE:-}" == "$name" && ! -e "$MOCK_PROTON_LOG.failed-once" ]]; then
      touch "$MOCK_PROTON_LOG.failed-once"
      exit 1
    fi
    rm -rf -- "${local_parent:?}/${name:?}"
    cp -a "$remote_source" "$local_parent/$name"
    if [[ "${MOCK_PROTON_CORRUPT_DOWNLOAD:-0}" == 1 && "$name" == archive.*.part-* ]]; then
      printf 'corrupt' >>"$local_parent/$name"
    fi
    ;;
  *)
    echo "mock received unsupported filesystem command: $command_name" >&2
    exit 2
    ;;
esac
