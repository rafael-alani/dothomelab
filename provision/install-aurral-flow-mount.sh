#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly source_path="/vault/shared/media/aurral-flows"
readonly target_path="/srv/appdata/docker/aurral/flows"
readonly unit_name="srv-appdata-docker-aurral-flows.mount"
readonly unit_source="$script_dir/$unit_name"
readonly unit_target="/etc/systemd/system/$unit_name"

[[ $EUID -eq 0 ]] || {
  echo "Run as root on the Proxmox host" >&2
  exit 1
}
[[ -d "$source_path" && ! -L "$source_path" ]] || {
  echo "Aurral flow source is missing or invalid: $source_path" >&2
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

install -m 0644 "$unit_source" "$unit_target"
systemctl daemon-reload
systemctl enable --now "$unit_name"

[[ "$(findmnt -n -o SOURCE -T "$target_path")" == \
  "/dev/sdb1[/shared/media/aurral-flows]" ||
  "$(findmnt -n -o SOURCE -T "$target_path")" == \
  "vault/shared[/media/aurral-flows]" ]] || {
  echo "$target_path is not the narrow Aurral flow bind" >&2
  exit 1
}

echo "Aurral flow bind is active and persistent"
