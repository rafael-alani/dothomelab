#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

for _ in {1..60}; do
  if docker inspect --format '{{.State.Health.Status}}' syncthing 2>/dev/null |
      grep -qx healthy; then
    break
  fi
  sleep 1
done

if ! docker inspect --format '{{.State.Health.Status}}' syncthing 2>/dev/null |
    grep -qx healthy; then
  echo "Syncthing did not become healthy" >&2
  exit 1
fi

python3 "$project_dir/configure-syncthing.py"
