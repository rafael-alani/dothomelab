#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-audiobookshelf}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:13378}"
readonly appdata_root="/srv/appdata/docker/audiobookshelf"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}} {{.Config.User}}' \
    audiobookshelf
)" || fail "Audiobookshelf container is missing"
read -r status project trigger image user <<<"$state"
[[ "$status" == "running" ]] || fail "Audiobookshelf is $status"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "Audiobookshelf project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Audiobookshelf is not enrolled in backup-gated WUD"
[[ "$image" == "ghcr.io/advplyr/audiobookshelf:latest" ]] ||
  fail "Audiobookshelf image is $image, expected the upstream latest channel"
[[ "$user" == "1000:1000" ]] ||
  fail "Audiobookshelf runs as $user, expected 1000:1000"

status_code="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "$APPS_URL/"
)" || fail "Audiobookshelf endpoint failed"
[[ "$status_code" == "200" ]] ||
  fail "Audiobookshelf returned HTTP $status_code"

database="$appdata_root/config/absdatabase.sqlite"
[[ -s "$database" ]] ||
  fail "Audiobookshelf database is missing or empty"
integrity="$(
  docker exec audiobookshelf node -e '
const sqlite3 = require("/app/node_modules/sqlite3");
const database = new sqlite3.Database(
  "/config/absdatabase.sqlite",
  sqlite3.OPEN_READONLY,
  (openError) => {
    if (openError) throw openError;
    database.get("PRAGMA integrity_check", (queryError, row) => {
      if (queryError) throw queryError;
      console.log(row.integrity_check);
      database.close((closeError) => {
        if (closeError) throw closeError;
      });
    });
  },
);
'
)"
[[ "$integrity" == "ok" ]] ||
  fail "Audiobookshelf database integrity is $integrity"
[[ "$(findmnt -n -o SOURCE -T "$database")" == "rpool/appdata/docker" ]] ||
  fail "Audiobookshelf database is not on canonical appdata"
for path in "$appdata_root" "$appdata_root/config" "$appdata_root/metadata"; do
  [[ "$(stat -c '%u:%g %a' "$path")" == "1000:1000 750" ]] ||
    fail "Audiobookshelf appdata ownership or mode drifted at $path"
done
[[ "$(findmnt -n -o SOURCE -T /data/media/audiobooks)" == vault/shared* ]] ||
  fail "Audiobookshelf media is not on vault/shared"
[[ "$(findmnt -n -o SOURCE -T /podcasts)" == vault/shared* ]] ||
  fail "Audiobookshelf podcasts are not on vault/shared"

docker inspect --format '{{json .Mounts}}' audiobookshelf |
  python3 -c '
import json
import sys

mounts = {mount["Destination"]: mount for mount in json.load(sys.stdin)}
expected = {
    "/config": ("/srv/appdata/docker/audiobookshelf/config", True),
    "/metadata": ("/srv/appdata/docker/audiobookshelf/metadata", True),
    "/audiobooks": ("/data/media/audiobooks", False),
    "/podcasts": ("/podcasts", True),
}
for destination, (source, writable) in expected.items():
    mount = mounts.get(destination)
    if mount is None:
        raise SystemExit(f"missing Audiobookshelf mount {destination}")
    if mount.get("Source") != source or bool(mount.get("RW")) != writable:
        raise SystemExit(
            f"Audiobookshelf mount drift for {destination}: "
            f"source={mount.get('Source')} rw={mount.get('RW')}"
        )
'

printf 'Audiobookshelf verification passed: HTTP=%s database=%s mounts, storage, identity, and WUD policy.\n' \
  "$status_code" "$integrity"
