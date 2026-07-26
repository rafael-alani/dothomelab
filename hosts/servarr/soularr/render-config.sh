#!/usr/bin/env bash
set -Eeuo pipefail

: "${LIDARR_API_KEY:?LIDARR_API_KEY is required}"
: "${SLSKD_API_KEY:?SLSKD_API_KEY is required}"

readonly target="/docker/soularr/config.ini"
readonly temporary="/docker/soularr/.config.ini.$$"

umask 077
trap 'rm -f -- "$temporary"' EXIT

sed \
  -e "s|@LIDARR_API_KEY@|$LIDARR_API_KEY|g" \
  -e "s|@SLSKD_API_KEY@|$SLSKD_API_KEY|g" \
  /opt/dothomelab/hosts/servarr/soularr/config.ini.template \
  >"$temporary"
chown 1000:1000 "$temporary"
chmod 0600 "$temporary"
mv -f "$temporary" "$target"
trap - EXIT

echo "Soularr config rendered without displaying credentials"
