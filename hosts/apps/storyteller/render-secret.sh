#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly env_file="${DOTHOMELAB_ENV:-/run/dothomelab.env}"
readonly destination="/srv/appdata/docker/storyteller/secrets/secret_key"
readonly temporary="${destination}.new"

# shellcheck disable=SC1091
source "$script_dir/../../common/load-env.sh"
load_dothomelab_env "$env_file"
: "${STORYTELLER_SECRET_KEY:?set STORYTELLER_SECRET_KEY in PVE /root/.env}"
(( ${#STORYTELLER_SECRET_KEY} >= 32 )) || {
  printf 'STORYTELLER_SECRET_KEY must contain at least 32 characters\n' >&2
  exit 1
}

umask 077
printf '%s\n' "$STORYTELLER_SECRET_KEY" >"$temporary"
chmod 0600 "$temporary"
if [[ -s "$destination" ]] && cmp -s "$temporary" "$destination"; then
  rm -f "$temporary"
else
  mv -f "$temporary" "$destination"
fi
chown 1000:1000 "$destination"
chmod 0600 "$destination"
printf 'Storyteller secret file rendered without displaying its value\n'
