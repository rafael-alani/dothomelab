#!/usr/bin/env bash
set -Eeuo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly appdata="/docker/sortarr"
readonly secrets_dir="$appdata/secrets"
readonly config="$appdata/Sortarr.env"
readonly startup_state="$appdata/Sortarr.startup.json"

required=(
  RADARR_API_KEY
  SONARR_API_KEY
  SORTARR_BASIC_AUTH_PASSWORD
  SORTARR_BASIC_AUTH_USER
  SORTARR_SECRET_KEY
)
for variable in "${required[@]}"; do
  [[ -n "${!variable:-}" ]] || {
    echo "$variable is missing from the loaded production environment" >&2
    exit 1
  }
done

[[ "${#SONARR_API_KEY}" -ge 16 ]] ||
  { echo "SONARR_API_KEY is too short" >&2; exit 1; }
[[ "${#RADARR_API_KEY}" -ge 16 ]] ||
  { echo "RADARR_API_KEY is too short" >&2; exit 1; }
[[ "${#SORTARR_BASIC_AUTH_PASSWORD}" -ge 20 ]] ||
  { echo "SORTARR_BASIC_AUTH_PASSWORD is too short" >&2; exit 1; }
[[ "${#SORTARR_SECRET_KEY}" -ge 64 ]] ||
  { echo "SORTARR_SECRET_KEY is too short" >&2; exit 1; }

install -d -o 1000 -g 1000 -m 0750 "$appdata"
install -d -o 1000 -g 1000 -m 0700 "$secrets_dir"

write_secret() {
  local destination="$1"
  local value="$2"
  local temporary
  temporary="$(mktemp "$secrets_dir/.secret.XXXXXX")"
  trap 'rm -f "$temporary"' RETURN
  chmod 0600 "$temporary"
  printf '%s' "$value" >"$temporary"
  chown 1000:1000 "$temporary"
  mv -f "$temporary" "$destination"
  trap - RETURN
}

write_secret "$secrets_dir/sonarr_api_key" "$SONARR_API_KEY"
write_secret "$secrets_dir/radarr_api_key" "$RADARR_API_KEY"
write_secret "$secrets_dir/basic_auth_password" "$SORTARR_BASIC_AUTH_PASSWORD"
write_secret "$secrets_dir/session_secret" "$SORTARR_SECRET_KEY"

temporary="$(mktemp "$appdata/.Sortarr.env.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
chmod 0600 "$temporary"
cat >"$temporary" <<EOF
MEDIA_SOURCE_PREFERENCE=arr
HISTORY_SOURCE_PREFERENCE=auto
SONARR_URL=http://sonarr:8989
SONARR_URL_API=http://sonarr:8989
SONARR_URL_EXTERNAL=https://sonarr.rafael.media
SONARR_API_KEY_FILE=/data/secrets/sonarr_api_key
RADARR_URL=http://radarr:7878
RADARR_URL_API=http://radarr:7878
RADARR_URL_EXTERNAL=https://radarr.rafael.media
RADARR_API_KEY_FILE=/data/secrets/radarr_api_key
SORTARR_AUTH_METHOD=basic
BASIC_AUTH_USER=$SORTARR_BASIC_AUTH_USER
BASIC_AUTH_PASS_FILE=/data/secrets/basic_auth_password
SORTARR_SECRET_KEY_FILE=/data/secrets/session_secret
SORTARR_PROXY_MODE=single
SORTARR_WAITRESS_TRUSTED_PROXY=192.168.0.110
SORTARR_PUBLIC_URL=https://sortarr.rafael.media
SORTARR_SESSION_COOKIE_SECURE=1
CACHE_SECONDS=300
SORTARR_STORE_SECRETS_AS_FILES=1
SORTARR_ALLOW_PLAINTEXT_SECRETS=0
SORTARR_ALLOW_UNSAFE_EPHEMERAL_RECOVERY=0
EOF
chown 1000:1000 "$temporary"
mv -f "$temporary" "$config"
trap - EXIT

if [[ ! -e "$startup_state" ]]; then
  install -o 1000 -g 1000 -m 0600 \
    "$script_dir/startup-state.json" \
    "$startup_state"
fi

echo "Sortarr Sonarr/Radarr, authentication, and single-proxy configuration rendered with file-based secrets"
