#!/usr/bin/env bash
set -Eeuo pipefail

: "${MOCK_PROTON_ROOT:?}"
: "${MOCK_PROTON_LOG:?}"

map_path() {
  case "$1" in
    /my-files)
      printf '%s/my-files\n' "$MOCK_PROTON_ROOT"
      ;;
    /my-files/*)
      printf '%s/my-files/%s\n' "$MOCK_PROTON_ROOT" "${1#/my-files/}"
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
    local_path="$(map_path "$1")"
    [[ -e "$local_path" ]]
    ;;
  create-folder)
    parent="$(map_path "$1")"
    name="$2"
    [[ -d "$parent" ]]
    mkdir "$parent/$name"
    ;;
  list)
    while [[ "${1:-}" == -* ]]; do
      case "$1" in
        -j)
          shift
          ;;
        -t)
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
      [[ -d "$child" ]] || continue
      name="$(basename "$child")"
      if [[ "$first" == true ]]; then
        first=false
      else
        printf ','
      fi
      jq -cn --arg name "$name" \
        '{uid:$name,type:"folder",name:{ok:true,value:$name}}'
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
    rm -rf -- "${local_parent:?}/${name:?}"
    cp -a "$remote_source" "$local_parent/$name"
    ;;
  *)
    echo "mock received unsupported filesystem command: $command_name" >&2
    exit 2
    ;;
esac
