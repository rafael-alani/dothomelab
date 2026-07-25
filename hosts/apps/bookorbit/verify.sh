#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  echo "FAIL $*" >&2
  exit 1
}

[[ "$(curl --silent --output /dev/null --write-out '%{http_code}' http://192.168.0.112:3002/api/v1/health)" == "200" ]] ||
  fail "BookOrbit health endpoint failed"
for container in bookorbit bookorbit-db; do
  [[ "$(docker inspect --format '{{.State.Health.Status}}' "$container")" == "healthy" ]] ||
    fail "$container is not healthy"
done
[[ "$(docker inspect --format '{{index .Config.Labels "wud.watch"}}' bookorbit)" == "true" ]] ||
  fail "BookOrbit is not enrolled in WUD"
[[ "$(docker inspect --format '{{index .Config.Labels "wud.watch"}}' bookorbit-db)" == "false" ]] ||
  fail "BookOrbit PostgreSQL must be excluded from WUD"
[[ "$(docker inspect --format '{{.Config.Image}}' bookorbit-db)" == "pgvector/pgvector:pg18" ]] ||
  fail "BookOrbit PostgreSQL image is not the explicit supported major"

docker inspect bookorbit |
  python3 -c '
import json
import sys
state = json.load(sys.stdin)[0]
if not state["HostConfig"]["ReadonlyRootfs"]:
    raise SystemExit("BookOrbit root filesystem is writable")
mounts = {item["Destination"]: item for item in state["Mounts"]}
for destination in ("/library/ebooks", "/library/pdfs", "/library/comics", "/library/mangas"):
    if destination not in mounts or mounts[destination]["RW"]:
        raise SystemExit(f"{destination} is not a read-only bind")
if not mounts.get("/data", {}).get("RW"):
    raise SystemExit("BookOrbit durable /data is not writable")
'

docker exec bookorbit-db psql \
  --dbname=bookorbit \
  --username=bookorbit \
  --no-align \
  --tuples-only \
  --command="
    SELECT count(*)
    FROM libraries
    WHERE name IN ('Ebooks', 'PDFs', 'Comics', 'Manga')
      AND file_write_enabled = false
      AND file_rename_enabled = false
  " |
  grep -qx 4 || fail "BookOrbit read-only library settings drifted"

if docker exec bookorbit sh -c 'touch /library/ebooks/.dothomelab-write-test' 2>/dev/null; then
  docker exec bookorbit rm -f /library/ebooks/.dothomelab-write-test
  fail "BookOrbit unexpectedly wrote to the canonical ebook library"
fi

echo "BookOrbit verification passed"
