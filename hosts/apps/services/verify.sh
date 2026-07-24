#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-apps-services}"
readonly APPS_HOST="${APPS_HOST:-192.168.0.112}"
readonly EXPECTED_VERSION="${EXPECTED_VERSION:-2.39.5}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

for container in portainer portainer_agent; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
      "$container"
  )" || fail "$container is missing"
  read -r status project trigger image <<<"$state"
  [[ "$status" == "running" ]] || fail "$container is $status"
  [[ "$project" == "$EXPECTED_PROJECT" ]] ||
    fail "$container project is $project, expected $EXPECTED_PROJECT"
  [[ "$trigger" == "docker.backupgated" ]] ||
    fail "$container is not enrolled in backup-gated WUD"
  [[ "$image" == *":$EXPECTED_VERSION" ]] ||
    fail "$container image is $image, expected $EXPECTED_VERSION"
done

status_payload="$(
  curl --insecure --fail --silent --show-error \
    "https://$APPS_HOST:9443/api/system/status"
)" || fail "Portainer status API failed"
reported_version="$(
  python3 -c 'import json,sys; print(json.load(sys.stdin).get("Version", ""))' \
    <<<"$status_payload"
)"
[[ "$reported_version" == "$EXPECTED_VERSION" ]] ||
  fail "Portainer API reports $reported_version, expected $EXPECTED_VERSION"

agent_status="$(
  curl --insecure --silent --show-error --output /dev/null \
    --write-out '%{http_code}' "https://$APPS_HOST:9001/ping"
)" || fail "Portainer Agent ping failed"
[[ "$agent_status" == "200" || "$agent_status" == "204" ]] ||
  fail "Portainer Agent ping returned HTTP $agent_status"

[[ -s /srv/appdata/docker/portainer/portainer.db ]] ||
  fail "Portainer database is missing from SSD appdata"

printf 'Apps Portainer verification passed: server=%s agent-tag=%s\n' \
  "$reported_version" "$EXPECTED_VERSION"
