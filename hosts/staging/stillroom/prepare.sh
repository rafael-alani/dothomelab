#!/usr/bin/env bash
# PVE-only preparation; exact new directories, no recursive permission changes.
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd -- "$here/../../.." && pwd)"
source "$repo/provision/inventory.env"
[[ $EUID -eq 0 ]] && command -v pct >/dev/null
[[ "$(findmnt -n -o SOURCE -T "$SHARED_MOUNT")" == "$SHARED_DATASET" ]]
[[ -d "$STAGING_PHOTOS_HOST_PATH" && ! -L "$STAGING_PHOTOS_HOST_PATH" ]]
if [[ ! -e "$STAGING_ARCHIVE_HOST_PATH" ]]; then
  install -d -m 0750 -o 101000 -g 101000 "$STAGING_ARCHIVE_HOST_PATH"
fi
[[ -d "$STAGING_ARCHIVE_HOST_PATH" && ! -L "$STAGING_ARCHIVE_HOST_PATH" ]]
[[ "$(stat -c '%u:%g' "$STAGING_ARCHIVE_HOST_PATH")" == '101000:101000' ]]
app="$STAGING_APPDATA_HOST_PATH/stillroom"
[[ -d "$app" && ! -L "$app" ]]
if [[ ! -e "$app/state" ]]; then
  install -d -m 0700 -o 101000 -g 101000 "$app/state"
fi
[[ -d "$app/state" && ! -L "$app/state" ]]
[[ "$(stat -c '%u:%g' "$app/state")" == '101000:101000' ]]
if [[ ! -e "$app/config.json" ]]; then
  install -m 0644 -o 100000 -g 100000 "$here/config.json" "$app/config.json"
fi
[[ -f "$app/config.json" && ! -L "$app/config.json" ]]
[[ "${1:-}" == --storage-only ]] && exit 0
for entry in "mp1|$STAGING_PHOTOS_HOST_PATH|$STAGING_PHOTOS_GUEST_PATH" \
             "mp2|$STAGING_ARCHIVE_HOST_PATH|$STAGING_ARCHIVE_GUEST_PATH"; do
  IFS='|' read -r slot host guest <<<"$entry"
  config="$(pct config 114)"
  if grep -q "^$slot:" <<<"$config"; then
    grep -Fqx "$slot: $host,mp=$guest" <<<"$config" || {
      echo "Conflicting staging mount: $slot" >&2; exit 1;
    }
  else
    # PVE 9 supports additive mount hotplug; no guest shutdown required.
    pct set 114 "--$slot" "$host,mp=$guest"
  fi
  if pct status 114 | grep -q running; then
    pct exec 114 -- mountpoint -q "$guest" || {
      echo 'Mount is configured but not live; do not deploy Stillroom' >&2; exit 1;
    }
  fi
done
