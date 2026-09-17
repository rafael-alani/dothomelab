#!/bin/sh
set -eu

# v1.0.38 no longer imports account settings from environment variables.
# Keep the recovery secret in the environment and materialize it privately in
# the replaceable container filesystem for upstream's ApiKeyFile support.
: "${ApiKey:?IMMICHFRAME_API_KEY must be supplied through Compose}"
umask 077
printf '%s' "$ApiKey" > /tmp/immichframe-api-key
unset ApiKey

# Import through upstream's supported first-start file migration. Never replace
# restored settings or modify the SQLite database ourselves.
if ! find /app/Config -maxdepth 1 -type f \( \
    -iname 'Settings.json' -o -iname 'Settings.yml' -o -iname 'Settings.yaml' \
    \) | grep -q .; then
    cp /dothomelab/Settings.seed.json /app/Config/Settings.json
fi

exec "$@"
