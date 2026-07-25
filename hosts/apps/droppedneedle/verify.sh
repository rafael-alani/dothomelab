#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-droppedneedle}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:8688}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    droppedneedle
)" || fail "DroppedNeedle container is missing"
read -r status health project trigger image <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "DroppedNeedle state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "DroppedNeedle project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "DroppedNeedle is not enrolled in backup-gated WUD"
[[ "$image" == "droppedneedle/droppedneedle:latest" ]] ||
  fail "DroppedNeedle image is $image, expected the upstream latest channel"

mounts="$(
  docker inspect --format \
    '{{range .Mounts}}{{println .Source "|" .Destination "|" .RW}}{{end}}' \
    droppedneedle
)"
for mapping in \
  '/srv/appdata/docker/droppedneedle/config | /app/config | true' \
  '/srv/appdata/docker/droppedneedle/cache | /app/cache | true' \
  '/srv/appdata/docker/droppedneedle/plugins | /app/plugins | true' \
  '/srv/appdata/docker/droppedneedle/imports | /app/imports | true' \
  '/music | /music | true' \
  '/slskd-downloads | /slskd-downloads | true'; do
  grep -Fqx "$mapping" <<<"$mounts" ||
    fail "DroppedNeedle mount is missing or read-only: $mapping"
done

for path in \
  /srv/appdata/docker/droppedneedle/config \
  /srv/appdata/docker/droppedneedle/cache \
  /srv/appdata/docker/droppedneedle/plugins \
  /srv/appdata/docker/droppedneedle/imports; do
  [[ -d "$path" ]] || fail "persistent path is missing: $path"
  [[ "$(findmnt -n -o SOURCE -T "$path")" == "rpool/appdata/docker" ]] ||
    fail "$path is not on canonical appdata"
done
[[ "$(findmnt -n -o SOURCE -T /music)" == vault/shared* ]] ||
  fail "DroppedNeedle music is not on vault/shared"
[[ "$(findmnt -n -o SOURCE -T /slskd-downloads)" == vault/shared* ]] ||
  fail "DroppedNeedle downloads are not on vault/shared"
[[ "$(stat -c '%d' /music)" == "$(stat -c '%d' /slskd-downloads)" ]] ||
  fail "DroppedNeedle music and download paths are not on the same filesystem"

network_id="$(docker network inspect --format '{{.Id}}' slskd-droppedneedle)" ||
  fail "shared slskd/DroppedNeedle network is missing"
container_network_id="$(
  docker inspect --format \
    '{{index .NetworkSettings.Networks "slskd-droppedneedle" "NetworkID"}}' \
    droppedneedle
)"
[[ "$container_network_id" == "$network_id" ]] ||
  fail "DroppedNeedle is not attached to the shared application network"

curl --fail --silent --show-error "$APPS_URL/health" >/dev/null ||
  fail "DroppedNeedle direct health endpoint failed"
docker exec droppedneedle \
  curl --fail --silent --show-error http://slskd:5030/health >/dev/null ||
  fail "DroppedNeedle cannot reach slskd over the private Docker network"

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    https://droppedneedle.rafael.media/
)" || fail "private DroppedNeedle HTTPS route failed"
[[ "$https_status" =~ ^(200|302|401)$ ]] ||
  fail "DroppedNeedle HTTPS route returned HTTP $https_status"

printf 'DroppedNeedle verification passed: health, durable state, slskd reachability, private HTTPS, and backup-gated WUD.\n'
