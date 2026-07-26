#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

if docker inspect droppedneedle >/dev/null 2>&1; then
  state="$(
    docker inspect --format \
      '{{.State.Running}} {{.HostConfig.RestartPolicy.Name}} {{.Config.Image}}' \
      droppedneedle
  )"
  [[ "$state" == "false no droppedneedle/droppedneedle:latest" ]] ||
    fail "retained DroppedNeedle container is running, restartable, or changed: $state"
fi

for path in \
  /srv/appdata/docker/droppedneedle/config \
  /srv/appdata/docker/droppedneedle/cache \
  /srv/appdata/docker/droppedneedle/plugins \
  /srv/appdata/docker/droppedneedle/imports; do
  [[ -d "$path" ]] || fail "retained path is missing: $path"
  [[ "$(findmnt -n -o SOURCE -T "$path")" == "rpool/appdata/docker" ]] ||
    fail "$path is not on canonical appdata"
done

docker network inspect slskd-droppedneedle >/dev/null ||
  fail "slskd rollback network is missing"
docker compose \
  -f /opt/dothomelab/hosts/apps/droppedneedle/compose.yaml \
  --profile rollback config --quiet ||
  fail "DroppedNeedle rollback Compose is invalid"
grep -q "RETIRED_CONTAINERS" \
  /opt/dothomelab/hosts/infra/wud/run-updates.py ||
  fail "WUD runner does not explicitly deny retired rollback containers"

printf 'DroppedNeedle retirement verification passed: stopped, non-restarting, WUD-denied, appdata and rollback Compose retained.\n'
