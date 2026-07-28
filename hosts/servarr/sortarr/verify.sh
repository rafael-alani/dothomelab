#!/usr/bin/env bash
set -Eeuo pipefail

readonly expected_image="ghcr.io/jaredharper1/sortarr:latest@sha256:9f78189af2e55e6a4de52138328be8119e51b7d42241020c2524a084822e57b6"
readonly appdata="/docker/sortarr"
readonly startup_state="$appdata/Sortarr.startup.json"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}}' \
    sortarr
)" || fail "Sortarr container is missing"
[[ "$state" == "running healthy sortarr false $expected_image" ]] ||
  fail "Sortarr state, image, project, or WUD policy drifted: $state"

docker inspect sortarr |
  python3 -c '
import json
import sys

item = json.load(sys.stdin)[0]
mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
if set(mounts) != {"/data"}:
    raise SystemExit(f"unexpected Sortarr mounts: {sorted(mounts)}")
data = mounts["/data"]
if data["Source"] != "/docker/sortarr" or not data["RW"]:
    raise SystemExit("Sortarr data mount drifted")
if "servarr-hello_default" not in item["NetworkSettings"]["Networks"]:
    raise SystemExit("Sortarr is not on the private Servarr network")
ports = item["HostConfig"]["PortBindings"]
if ports != {"8787/tcp": [{"HostIp": "192.168.0.102", "HostPort": "9595"}]}:
    raise SystemExit(f"Sortarr port binding drifted: {ports}")
environment = dict(value.split("=", 1) for value in item["Config"]["Env"])
expected = {
    "PUID": "1000",
    "PGID": "1000",
    "SORTARR_CONFIG_PATH": "/data/Sortarr.env",
    "SORTARR_ALLOW_PLAINTEXT_SECRETS": "0",
    "SORTARR_ALLOW_UNSAFE_EPHEMERAL_RECOVERY": "0",
    "SORTARR_PROXY_MODE": "single",
    "SORTARR_WAITRESS_TRUSTED_PROXY": "192.168.0.110",
}
for key, value in expected.items():
    if environment.get(key) != value:
        raise SystemExit(f"Sortarr environment drifted: {key}")
' || fail "Sortarr mount, network, port, or runtime security policy failed"

[[ "$(findmnt -n -o SOURCE -T "$appdata")" == "rpool/appdata/docker" ]] ||
  fail "Sortarr is not on canonical appdata"
[[ "$(stat -c '%u:%g %a' "$appdata")" == "1000:1000 750" ]] ||
  fail "Sortarr appdata ownership or mode drifted"
[[ "$(stat -c '%u:%g %a' "$appdata/secrets")" == "1000:1000 700" ]] ||
  fail "Sortarr secrets directory ownership or mode drifted"

for path in \
  "$appdata/Sortarr.env" \
  "$startup_state" \
  "$appdata/secrets/sonarr_api_key" \
  "$appdata/secrets/radarr_api_key" \
  "$appdata/secrets/basic_auth_password" \
  "$appdata/secrets/session_secret"; do
  [[ -s "$path" ]] || fail "Sortarr persistent file is missing: $path"
  [[ "$(stat -c '%u:%g %a' "$path")" == "1000:1000 600" ]] ||
    fail "Sortarr persistent file ownership or mode drifted: $path"
done

if ! python3 - "$startup_state" <<'PY'
import json
import sys

state = json.load(open(sys.argv[1], encoding="utf-8"))
if state != {"app_version": "0.9.0", "upgrade_setup_required": False}:
    raise SystemExit(f"Sortarr startup state drifted: {state}")
PY
then
  fail "Sortarr startup migration state failed"
fi

if ! python3 - "$appdata/Sortarr.env" <<'PY'
import sys
from pathlib import Path

values = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values[key] = value

expected = {
    "MEDIA_SOURCE_PREFERENCE": "arr",
    "SONARR_URL_API": "http://sonarr:8989",
    "SONARR_URL_EXTERNAL": "https://sonarr.rafael.media",
    "SONARR_API_KEY_FILE": "/data/secrets/sonarr_api_key",
    "RADARR_URL_API": "http://radarr:7878",
    "RADARR_URL_EXTERNAL": "https://radarr.rafael.media",
    "RADARR_API_KEY_FILE": "/data/secrets/radarr_api_key",
    "SORTARR_AUTH_METHOD": "basic",
    "BASIC_AUTH_PASS_FILE": "/data/secrets/basic_auth_password",
    "SORTARR_SECRET_KEY_FILE": "/data/secrets/session_secret",
    "SORTARR_PROXY_MODE": "single",
    "SORTARR_WAITRESS_TRUSTED_PROXY": "192.168.0.110",
    "SORTARR_PUBLIC_URL": "https://sortarr.rafael.media",
    "SORTARR_SESSION_COOKIE_SECURE": "1",
    "SORTARR_ALLOW_PLAINTEXT_SECRETS": "0",
    "SORTARR_ALLOW_UNSAFE_EPHEMERAL_RECOVERY": "0",
}
for key, value in expected.items():
    if values.get(key) != value:
        raise SystemExit(f"Sortarr configuration drifted: {key}")
for forbidden in (
    "SONARR_API_KEY",
    "RADARR_API_KEY",
    "BASIC_AUTH_PASS",
    "SORTARR_SECRET_KEY",
):
    if forbidden in values:
        raise SystemExit(f"Sortarr stores plaintext secret variable {forbidden}")
PY
then
  fail "Sortarr persistent configuration policy failed"
fi

unauthorized="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    http://192.168.0.102:9595/api/version
)" || fail "Sortarr unauthenticated boundary check failed"
[[ "$unauthorized" == "401" ]] ||
  fail "Sortarr unauthenticated API returned HTTP $unauthorized, expected 401"

auth_config="$(mktemp /run/sortarr-curl.XXXXXX)"
version_json="$(mktemp /run/sortarr-version.XXXXXX)"
config_json="$(mktemp /run/sortarr-config.XXXXXX)"
shows_json="$(mktemp /run/sortarr-shows.XXXXXX)"
movies_json="$(mktemp /run/sortarr-movies.XXXXXX)"
trap 'rm -f "$auth_config" "$version_json" "$config_json" "$shows_json" "$movies_json"' EXIT
chmod 0600 "$auth_config"
user="$(sed -n 's/^BASIC_AUTH_USER=//p' "$appdata/Sortarr.env")"
password="$(<"$appdata/secrets/basic_auth_password")"
printf 'user = "%s:%s"\n' "$user" "$password" >"$auth_config"
unset password

curl --fail --silent --show-error --config "$auth_config" \
  http://192.168.0.102:9595/api/version >"$version_json" ||
  fail "Sortarr authenticated direct API failed"
curl --fail --silent --show-error --config "$auth_config" \
  https://sortarr.rafael.media/api/config >"$config_json" ||
  fail "Sortarr authenticated HTTPS route failed"
curl --fail --silent --show-error --max-time 600 --config "$auth_config" \
  http://192.168.0.102:9595/api/shows >"$shows_json" ||
  fail "Sortarr Sonarr library API failed"
curl --fail --silent --show-error --max-time 600 --config "$auth_config" \
  http://192.168.0.102:9595/api/movies >"$movies_json" ||
  fail "Sortarr Radarr library API failed"

read -r version shows movies < <(
  python3 - "$version_json" "$config_json" "$shows_json" "$movies_json" <<'PY'
import json
import sys

version_payload = json.load(open(sys.argv[1], encoding="utf-8"))
config = json.load(open(sys.argv[2], encoding="utf-8"))
shows_payload = json.load(open(sys.argv[3], encoding="utf-8"))
movies_payload = json.load(open(sys.argv[4], encoding="utf-8"))

version = (
    version_payload.get("version") or version_payload.get("app_version", "")
    if isinstance(version_payload, dict)
    else str(version_payload)
)

expected_config = {
    "app_name": "Sortarr",
    "app_version": "0.9.0",
    "auth_method": "basic",
    "configured": True,
    "media_source": "arr",
    "radarr_configured": True,
    "radarr_url": "https://radarr.rafael.media",
    "request_authenticated_via": "basic",
    "setup_required": False,
    "sonarr_configured": True,
    "sonarr_url": "https://sonarr.rafael.media",
}
for key, value in expected_config.items():
    if config.get(key) != value:
        raise SystemExit(f"sanitized Sortarr config drifted: {key}")
if config.get("setup_reasons") != []:
    raise SystemExit(f"Sortarr setup reasons are not empty: {config['setup_reasons']}")

def count_rows(payload, keys):
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    return 0

shows = count_rows(shows_payload, ("shows", "series", "data", "items", "results"))
movies = count_rows(movies_payload, ("movies", "data", "items", "results"))
print(version, shows, movies)
PY
)
[[ "$version" == "0.9.0" ]] ||
  fail "Sortarr runtime version is $version, expected 0.9.0"
[[ "$shows" -gt 0 ]] || fail "Sortarr returned no Sonarr shows"
[[ "$movies" -gt 0 ]] || fail "Sortarr returned no Radarr movies"

printf 'Sortarr verification passed: v%s, Basic auth, private HTTPS route, %s shows, %s movies, canonical appdata, and manual-update policy.\n' \
  "$version" "$shows" "$movies"
