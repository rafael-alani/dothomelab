#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-slskd}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:5030}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.watch.digest"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    slskd
)" || fail "slskd container is missing"
read -r status health project watched digest trigger image <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "slskd state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "slskd project is $project, expected $EXPECTED_PROJECT"
[[ "$watched" == "true" && "$digest" == "true" &&
  "$trigger" == "docker.backupgated" ]] ||
  fail "slskd is not digest-watched through backup-gated WUD"
[[ "$image" == "slskd/slskd:latest" ]] ||
  fail "slskd image is $image, expected the upstream latest channel"

docker inspect --format '{{json .Config.Env}}' slskd |
  python3 -c '
import json
import sys

values = dict(item.split("=", 1) for item in json.load(sys.stdin))
expected = {
    "SLSKD_DOWNLOADS_DIR": "/slskd-downloads/complete",
    "SLSKD_INCOMPLETE_DIR": "/slskd-downloads/incomplete",
    "SLSKD_NO_HTTPS": "true",
    "SLSKD_REMOTE_CONFIGURATION": "false",
    "SLSKD_REMOTE_FILE_MANAGEMENT": "false",
    "SLSKD_SHARED_DIR": "/music",
}
drift = {key: values.get(key) for key, value in expected.items()
         if values.get(key) != value}
if drift:
    raise SystemExit(f"slskd environment drift: {drift}")
expected_cidrs = (
    "cidr=127.0.0.1/32,172.16.0.0/12,"
    "192.168.0.102/32,192.168.0.110/32"
)
if expected_cidrs not in values.get("SLSKD_API_KEY", "").split(";"):
    raise SystemExit("slskd API CIDRs do not match declared clients")
for key in ("SLSKD_SLSK_PASSWORD", "SLSKD_SLSK_USERNAME", "SLSKD_USERNAME"):
    if len(values.get(key, "")) < 3:
        raise SystemExit(f"slskd required environment is missing: {key}")
for key in ("SLSKD_JWT_KEY", "SLSKD_PASSWORD"):
    if len(values.get(key, "")) < 16:
        raise SystemExit(f"slskd secret is shorter than 16 characters: {key}")
if len(values.get("SLSKD_API_KEY", "").rsplit(";", 1)[-1]) < 16:
    raise SystemExit("slskd primary API key is shorter than 16 characters")
' || fail "slskd secure runtime configuration is missing or drifted"

mounts="$(
  docker inspect --format \
    '{{range .Mounts}}{{println .Source "|" .Destination "|" .RW}}{{end}}' \
    slskd
)"
grep -Fqx '/srv/appdata/docker/slskd | /app | true' <<<"$mounts" ||
  fail "slskd appdata mount is missing or read-only"
grep -Fqx '/music | /music | false' <<<"$mounts" ||
  fail "slskd music share is missing or not read-only"
grep -Fqx '/slskd-downloads | /slskd-downloads | true' <<<"$mounts" ||
  fail "slskd downloads mount is missing or read-only"

for path in /srv/appdata/docker/slskd /music /slskd-downloads; do
  [[ -d "$path" ]] || fail "persistent path is missing: $path"
done
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/slskd)" == "rpool/appdata/docker" ]] ||
  fail "slskd appdata is not on canonical SSD storage"
[[ "$(findmnt -n -o SOURCE -T /music)" == vault/shared* ]] ||
  fail "slskd music is not on vault/shared"
[[ "$(findmnt -n -o SOURCE -T /slskd-downloads)" == vault/shared* ]] ||
  fail "slskd downloads are not on vault/shared"
[[ "$(stat -c '%d' /music)" == "$(stat -c '%d' /slskd-downloads)" ]] ||
  fail "slskd music and download paths are not on the same filesystem"

network_id="$(docker network inspect --format '{{.Id}}' slskd-droppedneedle)" ||
  fail "shared slskd/DroppedNeedle network is missing"
container_network_id="$(
  docker inspect --format \
    '{{index .NetworkSettings.Networks "slskd-droppedneedle" "NetworkID"}}' \
    slskd
)"
[[ "$container_network_id" == "$network_id" ]] ||
  fail "slskd is not attached to the shared application network"

curl --fail --silent --show-error "$APPS_URL/health" >/dev/null ||
  fail "slskd direct health endpoint failed"
ss -lnt | grep -qE '192\.168\.0\.112:50300[[:space:]]' ||
  fail "slskd Soulseek peer port is not listening on Apps"

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://slskd.rafael.media/
)" || fail "private slskd HTTPS route failed"
[[ "$https_status" =~ ^(200|302|401)$ ]] ||
  fail "slskd HTTPS route returned HTTP $https_status"

api_key="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' slskd |
    sed -n 's/^SLSKD_API_KEY=.*;//p'
)"
version="$(
  docker exec slskd wget -q -O - \
    --header "X-API-Key: $api_key" \
    http://127.0.0.1:5030/api/v0/application |
    python3 -c '
import json
import sys
print(json.load(sys.stdin)["version"]["current"])
'
)" || fail "slskd authenticated application API failed"
unset api_key
[[ "$version" == 0.26.* ]] ||
  fail "slskd runtime is $version, expected stable 0.26.x"

printf 'slskd verification passed: stable latest client, authentication, storage, peer listener, rollback network, private HTTPS, and guarded WUD policy.\n'
