#!/usr/bin/env bash
set -Eeuo pipefail

state="$(
  docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    storyteller-reconciler
)"
[[ "$state" == "running healthy" ]] || {
  printf 'Storyteller reconciler is not healthy: %s\n' "$state" >&2
  exit 1
}

docker exec storyteller-reconciler \
  python /app/reconciler.py database-backup
