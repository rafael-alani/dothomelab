#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly -a sources=(
  "/vault/shared/media/books/ebooks"
  "/vault/shared/media/audiobooks"
)
readonly -a targets=(
  "/srv/appdata/docker/grimmory/libraries/ebooks"
  "/srv/appdata/docker/audiobookshelf/libraries/audiobooks"
)
readonly -a units=(
  "srv-appdata-docker-grimmory-libraries-ebooks.mount"
  "srv-appdata-docker-audiobookshelf-libraries-audiobooks.mount"
)

[[ $EUID -eq 0 ]] || {
  echo "Run as root on the Proxmox host" >&2
  exit 1
}

install -d -o 101000 -g 101000 -m 0750 \
  /srv/appdata/docker/grimmory \
  /srv/appdata/docker/grimmory/libraries \
  /srv/appdata/docker/audiobookshelf \
  /srv/appdata/docker/audiobookshelf/libraries

for index in "${!sources[@]}"; do
  source_path="${sources[$index]}"
  target_path="${targets[$index]}"
  unit_name="${units[$index]}"

  [[ -d "$source_path" && ! -L "$source_path" ]] || {
    echo "Grimmory library source is missing or invalid: $source_path" >&2
    exit 1
  }
  [[ "$(findmnt -n -o SOURCE -T "$source_path")" == "vault/shared" ]] || {
    echo "$source_path is not backed by vault/shared" >&2
    exit 1
  }

  install -d -o 101000 -g 101000 -m 0750 "$target_path"
  if [[ -n "$(find "$target_path" -mindepth 1 -maxdepth 1 -print -quit)" ]] &&
    ! mountpoint -q "$target_path"; then
    echo "Refusing to shadow non-empty appdata path $target_path" >&2
    exit 1
  fi

  install -m 0644 "$script_dir/$unit_name" "/etc/systemd/system/$unit_name"
done

systemctl daemon-reload
for unit_name in "${units[@]}"; do
  systemctl enable --now "$unit_name"
done

for index in "${!sources[@]}"; do
  actual_source="$(findmnt -n -o SOURCE -T "${targets[$index]}")"
  case "$actual_source" in
    "vault/shared["*"]" | "/dev/sdb1["*"]")
      ;;
    *)
      echo "${targets[$index]} is not a narrow vault/shared bind: $actual_source" >&2
      exit 1
      ;;
  esac
done

echo "Grimmory ebook and Audiobookshelf audiobook binds are active and persistent"
