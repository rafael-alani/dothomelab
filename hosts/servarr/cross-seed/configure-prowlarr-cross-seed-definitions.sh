#!/usr/bin/env bash
set -Eeuo pipefail

readonly reconciler="$(
  dirname -- "${BASH_SOURCE[0]}"
)/reconcile-prowlarr-cross-seed-definitions.py"

result="$("$reconciler" --apply)"
printf '%s\n' "$result"
if [[ "$result" == *"changed=true"* ]]; then
  docker restart prowlarr >/dev/null
  for _ in {1..60}; do
    if [[ "$(
      docker inspect --format '{{.State.Health.Status}}' prowlarr 2>/dev/null ||
        true
    )" == "healthy" ]]; then
      break
    fi
    sleep 2
  done
fi

[[ "$(docker inspect --format '{{.State.Health.Status}}' prowlarr)" == "healthy" ]] || {
  echo "Prowlarr did not become healthy after definition reconciliation" >&2
  exit 1
}

"$reconciler" --migrate
exec "$reconciler" --check
