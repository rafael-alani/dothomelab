#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

: "${DOTHOMELAB_ENV:=/run/dothomelab.env}"
# shellcheck disable=SC1091
source /opt/dothomelab/hosts/common/load-env.sh
load_dothomelab_env "$DOTHOMELAB_ENV"

readonly expected_image="ghcr.io/listenarrs/listenarr:canary-1.2.2@sha256:7aa44d67b649cd401507b763733f93e90ea4f12e2001e2bc67e31199366bb3a9"

[[ "$(docker inspect --format '{{.State.Health.Status}}' listenarr)" == "healthy" ]] ||
  fail "Listenarr is not healthy"
[[ "$(docker inspect --format '{{.Config.Image}}' listenarr)" == "$expected_image" ]] ||
  fail "Listenarr image is not pinned to the reviewed canary digest"
[[ "$(docker inspect --format '{{index .Config.Labels "wud.watch"}}' listenarr)" == "false" ]] ||
  fail "Listenarr must remain excluded from automatic WUD updates"

docker inspect listenarr |
  python3 -c '
import json
import sys

mounts = {item["Destination"]: item for item in json.load(sys.stdin)[0]["Mounts"]}
expected = {
    "/app/config": ("/docker/listenarr", True),
    "/audiobooks": ("/data/media/audiobooks", True),
    "/data/torrents": ("/data/torrents", True),
    "/downloads": ("/data/usernet", True),
}
for destination, (source, writable) in expected.items():
    mount = mounts.get(destination)
    if not mount or mount["Source"] != source:
        raise SystemExit(f"missing deterministic mount {destination}")
    if mount["RW"] is not writable:
        raise SystemExit(f"mount mode drift for {destination}")
'

[[ "$(findmnt -n -o SOURCE -T /data/media/audiobooks)" == "vault/shared"* ]] ||
  fail "Listenarr audiobook library is not on vault/shared"

bootstrap="$(
  curl --fail --silent --show-error \
    http://192.168.0.102:4545/api/v1/configuration/bootstrap
)"
python3 - "$bootstrap" <<'PY'
import json
import sys

state = json.loads(sys.argv[1])
if state.get("authenticationRequired") is not True:
    raise SystemExit("Listenarr authentication is not required")
PY

/opt/dothomelab/hosts/servarr/listenarr/render-config.py --check
/opt/dothomelab/hosts/servarr/listenarr/configure.py --check
/opt/dothomelab/hosts/servarr/listenarr/configure-qbittorrent-category.sh
/opt/dothomelab/hosts/servarr/listenarr/backup-database.sh

[[ -s /docker/listenarr/backups/latest/listenarr.db ]] ||
  fail "Listenarr latest SQLite recovery copy is missing"
python3 - /docker/listenarr/backups/latest/listenarr.db <<'PY'
import sqlite3
import sys

with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
if integrity != "ok":
    raise SystemExit(f"Listenarr recovery copy integrity is {integrity}")
PY

docker inspect shelfarr |
  python3 -c '
import json
import sys

mounts = {item["Destination"]: item for item in json.load(sys.stdin)[0]["Mounts"]}
if mounts.get("/audiobooks", {}).get("RW") is not False:
    raise SystemExit("Shelfarr still has write access to canonical audiobooks")
'

echo "Listenarr verification passed"
