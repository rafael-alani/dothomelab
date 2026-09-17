#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-immichframe}"
readonly APPS_URL="${APPS_URL:-http://192.168.0.112:8080}"
readonly IMMICH_URL="${IMMICH_URL:-http://192.168.0.112:2283}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}} {{.Config.Image}}' \
    immichframe
)" || fail "ImmichFrame container is missing"
read -r status project trigger image <<<"$state"
[[ "$status" == "running" ]] || fail "ImmichFrame is $status"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "ImmichFrame project is $project, expected $EXPECTED_PROJECT"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "ImmichFrame is not enrolled in backup-gated WUD"
[[ "$image" == "ghcr.io/immichframe/immichframe:latest" ]] ||
  fail "ImmichFrame image is $image, expected the upstream latest channel"

curl --fail --silent --show-error --output /dev/null "$IMMICH_URL/api/server/ping" ||
  fail "Immich dependency endpoint failed"
curl --fail --silent --show-error --output /dev/null "$APPS_URL/" ||
  fail "ImmichFrame endpoint failed"

api_key="$(
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' immichframe |
    sed -n 's/^ApiKey=//p'
)"
[[ -n "$api_key" ]] || fail "ImmichFrame API key is empty"
auth_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --header "x-api-key: $api_key" \
    "$IMMICH_URL/api/albums"
)" || fail "Immich API-key validation request failed"
unset api_key
[[ "$auth_status" == "200" ]] ||
  fail "Immich rejected the configured ImmichFrame album-read scope with HTTP $auth_status"

[[ "$(findmnt -n -o SOURCE -T /srv/appdata/docker/immichframe/config)" == \
  "rpool/appdata/docker" ]] ||
  fail "ImmichFrame config is not on canonical appdata"

docker exec immichframe sh -ec 'test -w /app/Config && test -s /tmp/immichframe-api-key' ||
  fail "ImmichFrame runtime cannot write its config or read its API-key file"

# A 200 from the UI also occurs on an unconfigured instance. Exercise the
# actual slideshow path, without printing photo metadata or credentials.
python3 - "$APPS_URL" <<'PY'
import json
import sqlite3
import sys
import urllib.request
import uuid

with sqlite3.connect(
    "file:/srv/appdata/docker/immichframe/config/immichframe.db?mode=ro", uri=True
) as db:
    assert db.execute("PRAGMA quick_check").fetchall() == [("ok",)], "Settings database failed quick_check"
    row = db.execute("SELECT Json FROM SettingsDocuments WHERE Id = 1").fetchone()
    assert row and json.loads(row[0]).get("Accounts"), "No configured Immich accounts"

base = sys.argv[1].rstrip("/")
with urllib.request.urlopen(base + "/api/Asset", timeout=60) as response:
    assets = json.load(response)
assert isinstance(assets, list) and assets, "Slideshow returned no assets"
asset_id = str(uuid.UUID(assets[0]["id"]))
with urllib.request.urlopen(base + "/api/Asset/" + asset_id + "/Asset", timeout=60) as response:
    assert response.headers.get_content_type().startswith("image/"), "Asset is not an image"
    assert response.read(1024), "Empty image response"
print(f"Slideshow verification passed: {len(assets)} assets and a non-empty image response.")
PY

printf 'ImmichFrame verification passed: slideshow, settings database, UI, Immich dependency, credential, storage, and WUD policy.\n'
