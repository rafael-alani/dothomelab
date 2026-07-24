#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_PROJECT="${EXPECTED_PROJECT:-paperless}"
readonly PAPERLESS_URL="${PAPERLESS_URL:-http://192.168.0.112:8002}"
readonly PAPERLESS_GPT_URL="${PAPERLESS_GPT_URL:-http://192.168.0.112:8003}"

: "${PAPERLESS_GPT_API_TOKEN:?set PAPERLESS_GPT_API_TOKEN}"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

for container in paperless-broker paperless-db paperless-ngx paperless-gpt; do
  state="$(
    docker inspect --format \
      '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}}' \
      "$container"
  )" || fail "$container is missing"
  read -r status health project <<<"$state"
  [[ "$status" == "running" && "$health" == "healthy" ]] ||
    fail "$container state is status=$status health=$health"
  [[ "$project" == "$EXPECTED_PROJECT" ]] ||
    fail "$container project is $project, expected $EXPECTED_PROJECT"
done

for container in paperless-ngx paperless-gpt; do
  trigger="$(
    docker inspect --format \
      '{{index .Config.Labels "wud.trigger.include"}}' "$container"
  )"
  [[ "$trigger" == "docker.backupgated" ]] ||
    fail "$container is not enrolled in backup-gated WUD"
done
for container in paperless-broker paperless-db; do
  watched="$(
    docker inspect --format '{{index .Config.Labels "wud.watch"}}' "$container"
  )"
  [[ "$watched" == "false" ]] ||
    fail "$container must remain excluded from automatic updates"
done

paperless_status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    "$PAPERLESS_URL/"
)" || fail "Paperless HTTP request failed"
[[ "$paperless_status" =~ ^(200|302)$ ]] ||
  fail "Paperless returned HTTP $paperless_status"

curl --fail --silent --show-error --output /dev/null \
  --header "Authorization: Token $PAPERLESS_GPT_API_TOKEN" \
  "$PAPERLESS_URL/api/documents/?page_size=1" ||
  fail "Paperless authenticated documents API failed"
curl --fail --silent --show-error --output /dev/null "$PAPERLESS_GPT_URL/" ||
  fail "Paperless-GPT UI failed"

read -r checksums users documents < <(
  docker exec paperless-db sh -ec '
    checksums="$(psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
      --no-align --tuples-only --command="SHOW data_checksums")"
    users="$(psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
      --no-align --tuples-only --command="SELECT count(*) FROM auth_user")"
    documents="$(psql --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
      --no-align --tuples-only --command="SELECT count(*) FROM documents_document")"
    printf "%s %s %s\n" "$checksums" "$users" "$documents"
  '
)
[[ "$checksums" == "on" ]] || fail "PostgreSQL data checksums are $checksums"
[[ "$users" -ge 2 ]] ||
  fail "Paperless is missing its administrator or dedicated GPT service account"

for path in \
  /srv/appdata/docker/paperless/data \
  /srv/appdata/docker/paperless/media \
  /srv/appdata/docker/paperless/postgres \
  /srv/appdata/docker/paperless/valkey \
  /srv/appdata/docker/paperless/gpt/config; do
  [[ -d "$path" ]] || fail "persistent path is missing: $path"
done

for url in \
  https://paperless.rafael.media/ \
  https://paperless-gpt.rafael.media/; do
  status="$(
    curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
      "$url"
  )" || fail "private HTTPS route failed: $url"
  [[ "$status" =~ ^(200|302)$ ]] ||
    fail "$url returned HTTP $status"
done

printf 'Paperless verification passed: users=%s documents=%s GPT=healthy HTTPS=private.\n' \
  "$users" "$documents"
