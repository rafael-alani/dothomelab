#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

for container in pinepods pinepods-db pinepods-valkey; do
  [[ "$(docker inspect --format '{{.State.Status}} {{.State.Health.Status}}' "$container")" == "running healthy" ]] ||
    fail "$container is not running and healthy"
done

state="$(
  docker inspect --format \
    '{{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.watch.digest"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    pinepods
)"
[[ "$state" == "pinepods true true docker.backupgated madeofpendletonwool/pinepods:latest" ]] ||
  fail "PinePods project, image, or backup-gated WUD policy drifted: $state"
[[ "$(docker inspect --format '{{.Config.Image}} {{index .Config.Labels "wud.watch"}}' pinepods-db)" == "postgres:18 false" ]] ||
  fail "PinePods PostgreSQL major or WUD exclusion drifted"
[[ "$(docker inspect --format '{{.Config.Image}} {{index .Config.Labels "wud.watch"}}' pinepods-valkey)" == "valkey/valkey:8-alpine false" ]] ||
  fail "PinePods Valkey major or WUD exclusion drifted"

health="$(
  curl --fail --silent --show-error http://192.168.0.112:8040/api/health
)"
python3 -c '
import json
import sys
state = json.loads(sys.argv[1])
if state.get("status") != "healthy":
    raise SystemExit("PinePods application status is not healthy")
if state.get("database") is not True or state.get("redis") is not True:
    raise SystemExit("PinePods database or Valkey readiness failed")
' "$health"
curl --fail --silent --show-error \
  http://192.168.0.112:8040/api/pinepods_check |
  python3 -c '
import json
import sys
state = json.load(sys.stdin)
if state.get("pinepods_instance") is not True:
    raise SystemExit("PinePods instance check failed")
'

docker inspect pinepods pinepods-db pinepods-valkey |
  python3 -c '
import json
import sys
containers = {item["Name"].lstrip("/"): item for item in json.load(sys.stdin)}
app = containers["pinepods"]
mounts = {mount["Destination"]: mount for mount in app["Mounts"]}
expected = {
    "/opt/pinepods/downloads": ("/podcasts/pinepods", True),
    "/opt/pinepods/backups": (
        "/srv/appdata/docker/pinepods/backups",
        True,
    ),
}
if set(mounts) != set(expected):
    raise SystemExit(f"unexpected PinePods mounts: {sorted(mounts)}")
for destination, (source, writable) in expected.items():
    mount = mounts[destination]
    if mount["Source"] != source or bool(mount["RW"]) != writable:
        raise SystemExit(f"PinePods mount drifted: {destination}")
for name in ("pinepods-db", "pinepods-valkey"):
    if containers[name]["HostConfig"].get("PortBindings"):
        raise SystemExit(f"{name} unexpectedly publishes a host port")
    labels = containers[name]["Config"].get("Labels") or {}
    if labels.get("com.docker.compose.project") != "pinepods":
        raise SystemExit(f"{name} is outside the PinePods project")
'

[[ "$(findmnt -n -o SOURCE -T /podcasts/pinepods)" == vault/shared* ]] ||
  fail "PinePods episodes are not on vault/shared"
[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/pinepods/postgres)" == rpool/appdata/docker ]] ||
  fail "PinePods PostgreSQL is not on canonical appdata"
[[ "$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' pinepods-db | sed -n 's/^PGDATA=//p')" == "/var/lib/pgdata/pgdata" ]] ||
  fail "PinePods PostgreSQL 18 data directory drifted"
docker top pinepods -eo uid,pid,comm |
  awk '
    NR == 1 { next }
    $3 == "docker-init" && $1 == 0 { init_seen = 1; next }
    $1 != 1000 { bad = 1 }
    END { exit (!init_seen || bad) }
  ' ||
  fail "PinePods application processes do not run as PUID 1000 below docker-init"

docker exec pinepods-db psql \
  --dbname=pinepods \
  --username=pinepods \
  --no-align \
  --tuples-only \
  --command='
    SELECT count(*)
    FROM information_schema.tables
    WHERE table_schema = '"'"'public'"'"'
      AND table_name IN (
        '"'"'Users'"'"',
        '"'"'Podcasts'"'"',
        '"'"'Episodes'"'"',
        '"'"'DownloadedEpisodes'"'"',
        '"'"'UserEpisodeHistory'"'"',
        '"'"'GpodderDevices'"'"'
      )
  ' |
  grep -qx 6 || fail "PinePods application schema is incomplete"

printf 'PinePods verification passed: application/DB/Valkey health, PG18 layout, PUID, private network, narrow episode mount, and WUD policy.\n'
