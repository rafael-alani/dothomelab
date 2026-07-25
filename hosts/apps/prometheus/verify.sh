#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-prometheus}"
readonly EXPECTED_IMAGE="${EXPECTED_IMAGE:-prom/prometheus:v3.13.1}"
readonly PROMETHEUS_URL="${PROMETHEUS_URL:-http://192.168.0.112:9090}"
readonly PROMETHEUS_HTTPS_URL="${PROMETHEUS_HTTPS_URL:-https://prometheus.rafael.media}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.watch"}} {{.Config.Image}}' \
    prometheus
)" || fail "prometheus is missing"
read -r status health project watched image <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "prometheus state is status=$status health=$health"
[[ "$project" == "$EXPECTED_PROJECT" ]] ||
  fail "prometheus project is $project, expected $EXPECTED_PROJECT"
[[ "$watched" == "false" ]] ||
  fail "prometheus must remain excluded from automatic updates"
[[ "$image" == "$EXPECTED_IMAGE" ]] ||
  fail "prometheus image is $image, expected $EXPECTED_IMAGE"

curl --fail --silent --show-error --output /dev/null \
  "$PROMETHEUS_URL/-/ready" ||
  fail "Prometheus readiness endpoint failed"
curl --fail --silent --show-error \
  "$PROMETHEUS_URL/api/v1/query?query=up" |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
if payload.get("status") != "success":
    raise SystemExit("Prometheus query API did not return success")
results = payload.get("data", {}).get("result", [])
jobs = {
    item.get("metric", {}).get("job")
    for item in results
    if item.get("value", [None, "0"])[1] == "1"
}
missing = {"prometheus", "loki"} - jobs
if missing:
    raise SystemExit(f"Prometheus is missing healthy scrape jobs: {sorted(missing)}")
' || fail "Prometheus does not report both declared scrape jobs up"

[[ "$(findmnt -n -o SOURCE --target /srv/appdata/docker)" == "rpool/appdata/docker" ]] ||
  fail "Prometheus appdata is not on rpool/appdata/docker"
[[ -d /srv/appdata/docker/prometheus ]] ||
  fail "Prometheus persistent data directory is missing"
[[ "$(stat -c '%u:%g' /srv/appdata/docker/prometheus)" == "65534:65534" ]] ||
  fail "Prometheus persistent data directory ownership drifted"
docker network inspect dothomelab-observability >/dev/null ||
  fail "shared observability Docker network is missing"

curl --fail --silent --show-error --output /dev/null \
  "$PROMETHEUS_HTTPS_URL/-/ready" ||
  fail "private Prometheus HTTPS route failed"

printf 'Prometheus verification passed: image=%s TSDB=appdata HTTPS=private.\n' \
  "$image"
