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
    '{{.State.Status}} {{.State.Health.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{index .Config.Labels "wud.watch.digest"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}} {{.Config.User}}' \
    audiobookshelf
)" || fail "Audiobookshelf container is missing"
read -r status health project watched digest trigger image user <<<"$state"
[[ "$status" == "running" ]] || fail "Audiobookshelf is $status"
[[ "$health" == "healthy" ]] || fail "Audiobookshelf health is $health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "Audiobookshelf project is $project, expected $EXPECTED_PROJECT"
[[ "$watched" == "true" && "$digest" == "true" ]] ||
  fail "Audiobookshelf rolling-image WUD policy drifted"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Audiobookshelf is not enrolled in backup-gated WUD"
[[ "$image" == "ghcr.io/advplyr/audiobookshelf:latest" ]] ||
  fail "Audiobookshelf image is $image, expected the upstream latest channel"
[[ "$user" == "1000:1000" ]] ||
  fail "Audiobookshelf runs as $user, expected 1000:1000"

docker inspect audiobookshelf |
  python3 -c '
import json
import sys

container = json.load(sys.stdin)[0]
host = container["HostConfig"]
if not host.get("ReadonlyRootfs"):
    raise SystemExit("Audiobookshelf root filesystem is writable")
if set(host.get("CapDrop") or []) != {"ALL"}:
    raise SystemExit("Audiobookshelf capabilities are not dropped")
if "no-new-privileges:true" not in (host.get("SecurityOpt") or []):
    raise SystemExit("Audiobookshelf no-new-privileges policy drifted")
'

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

docker exec audiobookshelf node -e '
const sqlite3 = require("/app/node_modules/sqlite3");
const database = new sqlite3.Database(
  "/config/absdatabase.sqlite",
  sqlite3.OPEN_READONLY,
  (openError) => {
    if (openError) throw openError;
    database.serialize(() => {
      database.all(
        `SELECT l.id, l.name, l.mediaType, l.settings, f.path AS fullPath
           FROM libraries l
           JOIN libraryFolders f ON f.libraryId = l.id
          WHERE l.mediaType = "book" AND f.path = "/audiobooks"`,
        (libraryError, libraries) => {
          if (libraryError) throw libraryError;
          database.all(
            `SELECT l.id, l.name, l.mediaType, f.path AS fullPath
               FROM libraries l
               JOIN libraryFolders f ON f.libraryId = l.id
              WHERE l.mediaType = "podcast" AND f.path = "/podcasts"`,
            (podcastError, podcastLibraries) => {
              if (podcastError) throw podcastError;
              database.all(
                `SELECT id, type, username, isActive, permissions
                   FROM users
                  WHERE username = "shelfarr-integration"`,
                (userError, users) => {
                  if (userError) throw userError;
                  database.all(
                    `SELECT name, isActive, userId
                       FROM apiKeys
                      WHERE name = "Shelfarr audiobook library scan"`,
                    (keyError, keys) => {
                      if (keyError) throw keyError;
                      process.stdout.write(JSON.stringify({
                        libraries,
                        podcastLibraries,
                        users,
                        keys,
                      }));
                      database.close((closeError) => {
                        if (closeError) throw closeError;
                      });
                    },
                  );
                },
              );
            },
          );
        },
      );
    });
  },
);
' |
  python3 -c '
import json
import sys

state = json.load(sys.stdin)
if len(state["libraries"]) != 1:
    raise SystemExit("expected one Audiobookshelf /audiobooks library")
library = state["libraries"][0]
settings = json.loads(library["settings"])
expected_settings = {
    "disableWatcher": True,
    "autoScanCronExpression": "0 4 * * *",
    "audiobooksOnly": True,
}
for key, expected in expected_settings.items():
    if settings.get(key) != expected:
        raise SystemExit(f"Audiobookshelf setting drifted: {key}")
if settings.get("metadataPrecedence", [None])[0] != "folderStructure":
    raise SystemExit("folder structure is not first in metadata precedence")
if len(state["podcastLibraries"]) != 1:
    raise SystemExit("retained Audiobookshelf /podcasts library is missing")
if state["podcastLibraries"][0]["name"] != "Podcasts":
    raise SystemExit("retained Audiobookshelf Podcasts library name drifted")
if len(state["users"]) != 1:
    raise SystemExit("expected one Shelfarr Audiobookshelf integration user")
user = state["users"][0]
permissions = json.loads(user["permissions"])
if user["type"] != "admin" or not user["isActive"]:
    raise SystemExit("Shelfarr Audiobookshelf integration user drifted")
for key in (
    "download",
    "update",
    "delete",
    "upload",
    "createEreader",
    "accessAllLibraries",
    "accessAllTags",
    "accessExplicitContent",
    "selectedTagsNotAccessible",
):
    if permissions.get(key) is not False:
        raise SystemExit(f"Shelfarr integration permission drifted: {key}")
if permissions.get("librariesAccessible") != [library["id"]]:
    raise SystemExit("Shelfarr integration library scope drifted")
if not any(
    key["isActive"] and key["userId"] == user["id"]
    for key in state["keys"]
):
    raise SystemExit("active Shelfarr Audiobookshelf API key is missing")
'

[[ "$(findmnt -n -o SOURCE -T "$database")" == "rpool/appdata/docker" ]] ||
  fail "Audiobookshelf database is not on canonical appdata"
for path in "$appdata_root" "$appdata_root/config" "$appdata_root/metadata"; do
  [[ "$(stat -c '%u:%g %a' "$path")" == "1000:1000 750" ]] ||
    fail "Audiobookshelf appdata ownership or mode drifted at $path"
done
[[ "$(findmnt -n -o SOURCE -T /data/media/audiobooks)" == vault/shared* ]] ||
  fail "Audiobookshelf media is not on vault/shared"
docker exec audiobookshelf test -r /audiobooks ||
  fail "Audiobookshelf cannot read /audiobooks"

docker inspect --format '{{json .Mounts}}' audiobookshelf |
  python3 -c '
import json
import sys

mounts = {mount["Destination"]: mount for mount in json.load(sys.stdin)}
expected = {
    "/config": ("/srv/appdata/docker/audiobookshelf/config", True),
    "/metadata": ("/srv/appdata/docker/audiobookshelf/metadata", True),
    "/audiobooks": ("/data/media/audiobooks", False),
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
if "/podcasts" in mounts:
    raise SystemExit("Audiobookshelf retained podcast library is still writable")
'

printf 'Audiobookshelf verification passed: HTTP=%s database=%s scoped scan identity, immutable audiobooks, inactive retained podcast library, hardening, mounts, and WUD policy.\n' \
  "$status_code" "$integrity"
