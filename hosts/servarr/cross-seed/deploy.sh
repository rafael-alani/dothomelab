#!/usr/bin/env bash
set -Eeuo pipefail

readonly compose="/opt/dothomelab/hosts/servarr/cross-seed/compose.yaml"
readonly approval="/docker/cross-seed/indexers-approved"

docker compose -f "$compose" config --quiet
docker compose -f "$compose" pull

if [[ -s "$approval" ]]; then
  docker compose -f "$compose" up -d
  docker update --restart unless-stopped cross-seed >/dev/null
  echo "cross-seed deployed after manual indexer approval"
else
  docker compose -f "$compose" stop
  docker compose -f "$compose" create
  echo "cross-seed image and container are prepared but stopped pending manual indexer approval"
fi
