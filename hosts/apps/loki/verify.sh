#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-loki}"
readonly EXPECTED_IMAGE="${EXPECTED_IMAGE:-grafana/loki:3.7.3}"
readonly LOKI_URL="${LOKI_URL:-http://192.168.0.112:3100}"
readonly LOKI_HTTPS_URL="${LOKI_HTTPS_URL:-https://loki.rafael.media}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}}' \
    loki
)" || fail "loki is missing"
read -r status project watched image <<<"$state"
[[ "$status" == "running" ]] || fail "loki state is $status"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "loki project is $project, expected $EXPECTED_PROJECT"
[[ "$watched" == "false" ]] ||
  fail "loki must remain excluded from automatic updates"
[[ "$image" == "$EXPECTED_IMAGE" ]] ||
  fail "loki image is $image, expected $EXPECTED_IMAGE"

curl --fail --silent --show-error --output /dev/null "$LOKI_URL/ready" ||
  fail "Loki readiness endpoint failed"
curl --fail --silent --show-error "$LOKI_URL/loki/api/v1/status/buildinfo" |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
if payload.get("version") != "3.7.3":
    raise SystemExit(f"unexpected Loki version: {payload.get('version')}")
' || fail "Loki build information did not report version 3.7.3"
curl --fail --silent --show-error "$LOKI_URL/loki/api/v1/labels" |
  python3 -c '
import json
import sys

if json.load(sys.stdin).get("status") != "success":
    raise SystemExit("Loki labels API did not return success")
' || fail "Loki query API failed"

[[ "$(findmnt -n -o SOURCE --target /srv/appdata/docker)" == "rpool/appdata/docker" ]] ||
  fail "Loki appdata is not on rpool/appdata/docker"
for path in chunks compactor rules; do
  full_path="/srv/appdata/docker/loki/$path"
  [[ -d "$full_path" ]] || fail "Loki persistent path is missing: $full_path"
  [[ "$(stat -c '%u:%g' "$full_path")" == "10001:10001" ]] ||
    fail "Loki persistent path ownership drifted: $full_path"
done
docker network inspect dothomelab-observability >/dev/null ||
  fail "shared observability Docker network is missing"

curl --fail --silent --show-error --output /dev/null \
  "$LOKI_HTTPS_URL/ready" ||
  fail "private Loki HTTPS route failed"

printf 'Loki verification passed: image=%s TSDB/filesystem=appdata HTTPS=private.\n' \
  "$image"
