#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

[[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  http://192.168.0.112:6060/api/v1/healthcheck)" == "200" ]] ||
  fail "Grimmory health endpoint failed"

for container in grimmory grimmory-db; do
  state="$(docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}}' \
    "$container")"
  [[ "$state" == "running healthy grimmory" ]] ||
    fail "$container state drifted: $state"
done

[[ "$(docker inspect --format '{{.Config.Image}}' grimmory)" == \
  "ghcr.io/grimmory-tools/grimmory:latest" ]] ||
  fail "Grimmory is not on the official stable rolling channel"
[[ "$(docker inspect --format '{{index .Config.Labels "wud.watch"}}' grimmory)" == "true" ]] ||
  fail "Grimmory is not enrolled in WUD"
[[ "$(docker inspect --format '{{index .Config.Labels "wud.trigger.include"}}' grimmory)" == \
  "docker.backupgated" ]] ||
  fail "Grimmory is not backup gated"
[[ "$(docker inspect --format '{{.Config.Image}}' grimmory-db)" == \
  "lscr.io/linuxserver/mariadb:11.4.8" ]] ||
  fail "Grimmory MariaDB image drifted"
[[ "$(docker inspect --format '{{index .Config.Labels "wud.watch"}}' grimmory-db)" == "false" ]] ||
  fail "Grimmory MariaDB must remain a manual update"

docker inspect grimmory |
  python3 -c '
import json
import sys

state = json.load(sys.stdin)[0]
mounts = {item["Destination"]: item for item in state["Mounts"]}
expected = {
    "/app/data": ("/srv/appdata/docker/grimmory/data", True),
    "/library/ebooks": (
        "/srv/appdata/docker/grimmory/libraries/ebooks",
        True,
    ),
    "/library/audiobooks": (
        "/data/media/audiobooks",
        False,
    ),
}
for destination, (source, writable) in expected.items():
    mount = mounts.get(destination)
    if not mount:
        raise SystemExit(f"missing Grimmory mount {destination}")
    if mount["Source"] != source or mount["RW"] != writable:
        raise SystemExit(f"Grimmory mount drifted: {destination}")
if "no-new-privileges" not in state["HostConfig"]["SecurityOpt"]:
    raise SystemExit("Grimmory no-new-privileges policy drifted")
'

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/grimmory/data)" == \
  "rpool/appdata/docker" ]] ||
  fail "Grimmory state is not on canonical appdata"
for path in /srv/appdata/docker/grimmory/libraries/ebooks; do
  source="$(findmnt -n -o SOURCE -T "$path")"
  [[ "$source" == "vault/shared["*"]" || "$source" == "/dev/sdb1["*"]" ]] ||
    fail "$path is not a narrow canonical-media bind"
done
docker exec grimmory test -r /library/audiobooks ||
  fail "Grimmory cannot read canonical audiobooks"
if docker exec grimmory test -w /library/audiobooks; then
  fail "Grimmory can write canonical audiobooks"
fi

docker exec grimmory-db mariadb \
  --user=grimmory \
  --password="$(
    docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' grimmory-db |
      sed -n 's/^MYSQL_PASSWORD=//p'
  )" \
  --batch \
  --skip-column-names \
  --execute='SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = "grimmory";' \
  grimmory |
  awk '$1 > 0 {found=1} END {exit !found}' ||
  fail "Grimmory MariaDB schema is empty"

echo "Grimmory service, database, writable ebooks, read-only audiobooks, hardening, and WUD policy verified"
