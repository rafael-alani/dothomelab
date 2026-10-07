#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPS_URL="${APPS_URL:-http://192.168.0.112:8088}"
readonly HTTPS_URL="${HTTPS_URL:-https://zotero.rafael.media}"

: "${ZOTERO_WEBDAV_USERNAME:?set ZOTERO_WEBDAV_USERNAME}"
: "${ZOTERO_WEBDAV_PASSWORD:?set ZOTERO_WEBDAV_PASSWORD}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "wud.trigger.include"}}' \
    zotero-webdav
)" || fail "Zotero WebDAV container is missing"
read -r status health project trigger <<<"$state"
[[ "$status" == "running" && "$health" == "healthy" ]] ||
  fail "Zotero WebDAV state is status=$status health=$health"
[[ "$project" == "zotero-webdav" ]] || fail "unexpected project $project"
[[ "$trigger" == "docker.backupgated" ]] ||
  fail "Zotero WebDAV is not enrolled in backup-gated WUD"

curl --fail --silent --show-error --output /dev/null "$APPS_URL/health" ||
  fail "health endpoint failed"

unauthenticated="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --request PROPFIND "$APPS_URL/zotero/"
)"
[[ "$unauthenticated" == "401" ]] ||
  fail "unauthenticated PROPFIND returned HTTP $unauthenticated"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
test_name="dothomelab-verify-$$.txt"
printf 'dothomelab zotero webdav verification\n' >"$tmp_dir/source"

auth=(--connect-timeout 10 --max-time 60 --user "$ZOTERO_WEBDAV_USERNAME:$ZOTERO_WEBDAV_PASSWORD")
propfind="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "${auth[@]}" --request PROPFIND "$APPS_URL/zotero/"
)"
[[ "$propfind" == "207" ]] ||
  fail "authenticated PROPFIND returned HTTP $propfind"

curl --fail --silent --show-error "${auth[@]}" \
  --upload-file "$tmp_dir/source" "$APPS_URL/zotero/$test_name" ||
  fail "PUT failed"
curl --fail --silent --show-error "${auth[@]}" \
  --output "$tmp_dir/result" "$APPS_URL/zotero/$test_name" ||
  fail "GET failed"
cmp "$tmp_dir/source" "$tmp_dir/result" || fail "GET content differs from PUT"
# Exercise the client-facing route as well as the direct service. A healthy
# container alone does not prove DNS, TLS, and proxy download/upload work.
curl --fail --silent --show-error "${auth[@]}" \
  --output "$tmp_dir/https-result" "$HTTPS_URL/zotero/$test_name" ||
  fail "HTTPS GET failed"
cmp "$tmp_dir/source" "$tmp_dir/https-result" || fail "HTTPS GET content differs"
curl --fail --silent --show-error "${auth[@]}" \
  --upload-file "$tmp_dir/source" "$HTTPS_URL/zotero/$test_name" ||
  fail "HTTPS PUT failed"
curl --fail --silent --show-error "${auth[@]}" \
  --output "$tmp_dir/https-result" "$HTTPS_URL/zotero/$test_name" ||
  fail "HTTPS GET after PUT failed"
cmp "$tmp_dir/source" "$tmp_dir/https-result" || fail "HTTPS PUT/GET content differs"
curl --fail --silent --show-error "${auth[@]}" \
  --request DELETE "$APPS_URL/zotero/$test_name" ||
  fail "DELETE failed"

https_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "${auth[@]}" --request PROPFIND "$HTTPS_URL/zotero/"
)"
[[ "$https_status" == "207" ]] ||
  fail "HTTPS PROPFIND returned HTTP $https_status"

printf 'Zotero WebDAV verification passed: auth, PROPFIND, PUT/GET, checksum, DELETE, and HTTPS.\n'
