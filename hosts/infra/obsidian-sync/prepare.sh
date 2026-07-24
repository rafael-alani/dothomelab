#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
vault_dir=/vault/shared/media/obsidian
versions_dir=/vault/shared/media/.obsidian-versions
photos_dir=/vault/shared/media/photos
proton_work=/vault/shared/.proton-backup-work
syncthing_state=/srv/appdata/docker/syncthing
proton_state=/srv/appdata/docker/proton-drive

require_source_prefix() {
  local path="$1"
  local expected="$2"
  local source
  source="$(findmnt -n -o SOURCE -T "$path")"
  if [[ "$source" != "$expected"* ]]; then
    echo "$path is backed by $source, expected $expected" >&2
    exit 1
  fi
}

require_source_prefix /vault/shared vault/shared
require_source_prefix /srv/appdata/docker rpool/appdata/docker

if [[ "$(uname -m)" != x86_64 ]]; then
  echo "The pinned Proton CLI image currently targets Infra's x86_64 architecture" >&2
  exit 1
fi

for path in "$vault_dir" "$versions_dir" "$proton_work"; do
  if [[ -e "$path" ]] && [[ ! -d "$path" ]]; then
    echo "$path exists but is not a directory" >&2
    exit 1
  fi
  if [[ ! -e "$path" ]]; then
    if [[ "$path" == "$proton_work" ]]; then
      install -d -o 1000 -g 1000 -m 0700 "$path"
    else
      install -d -o 1000 -g 1000 -m 0750 "$path"
    fi
  fi
done

[[ -d "$photos_dir" ]] || {
  echo "Missing photo backup source: $photos_dir" >&2
  exit 1
}

install -d -o 1000 -g 1000 -m 0750 "$syncthing_state" "$proton_state"

if [[ ! -e "$vault_dir/.stignore" ]]; then
  install -o 1000 -g 1000 -m 0640 "$project_dir/stignore.example" "$vault_dir/.stignore"
fi

for path in \
  "$vault_dir" \
  "$versions_dir" \
  "$photos_dir" \
  "$proton_work" \
  "$syncthing_state" \
  "$proton_state"; do
  if [[ "$(stat -c %u "$path")" != 1000 ]] || [[ "$(stat -c %g "$path")" != 1000 ]]; then
    echo "$path must be writable by UID:GID 1000:1000; inspect before changing ownership" >&2
    exit 1
  fi
done

chmod 0700 "$proton_work"

echo "Prepared Syncthing and Proton backup storage without recursive permission changes"
