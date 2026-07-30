#!/usr/bin/env bash
set -Eeuo pipefail

readonly compose="/opt/dothomelab/hosts/servarr/cross-seed/compose.yaml"
readonly approval="/docker/cross-seed/indexers-approved"

docker compose -f "$compose" config --quiet
docker compose -f "$compose" pull

if [[ -s "$approval" ]]; then
  docker compose -f "$compose" up -d
  # config.js is a bind-mounted generated file. Compose does not recreate the
  # container when only its contents change, so restart it to load the exact
  # reconciled tracker allowlist.
  docker restart cross-seed >/dev/null
  for _ in {1..60}; do
    [[ "$(
      docker inspect --format '{{.State.Health.Status}}' cross-seed \
        2>/dev/null || true
    )" == "healthy" ]] && break
    sleep 2
  done
  [[ "$(docker inspect --format '{{.State.Health.Status}}' cross-seed)" == \
    "healthy" ]] || {
    echo "cross-seed did not become healthy after configuration reload" >&2
    exit 1
  }
  docker update --restart unless-stopped cross-seed >/dev/null
  echo "cross-seed deployed after manual indexer approval"
else
  docker compose -f "$compose" stop
  docker compose -f "$compose" create
  echo "cross-seed image and container are prepared but stopped pending manual indexer approval"
fi
