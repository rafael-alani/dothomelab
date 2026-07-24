#!/usr/bin/env bash
set -euo pipefail

compose_file="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/compose.yaml"
failures=0

check() {
  local description="$1"
  shift
  if "$@"; then
    printf 'ok - %s\n' "$description"
  else
    printf 'FAIL - %s\n' "$description" >&2
    failures=$((failures + 1))
  fi
}

check "Compose renders" docker compose -f "$compose_file" config --quiet
check "Syncthing is healthy" test \
  "$(docker inspect --format '{{.State.Health.Status}}' syncthing 2>/dev/null)" = healthy
check "GUI listens only on loopback" bash -c \
  "ss -lnt | awk '{print \$4}' | grep -qx '127.0.0.1:8384'"
check "sync TCP port listens" bash -c \
  "ss -lnt | awk '{print \$4}' | grep -Eq '(^|:)22000$'"
check "vault marker exists" test -d /vault/shared/media/obsidian/.stfolder
check "version directory exists" test -d /vault/shared/media/.obsidian-versions
check "Syncthing mount is read-write" bash -c \
  "docker inspect syncthing --format '{{range .Mounts}}{{if eq .Destination \"/vault\"}}{{.RW}}{{end}}{{end}}' | grep -qx true"
check "Proton vault mount is read-only" bash -c \
  "docker compose -f '$compose_file' --profile proton config | grep -A5 'source: /vault/shared/media/obsidian' | grep -q 'read_only: true'"
check "Proton CLI image is runnable" docker compose -f "$compose_file" \
  --profile proton run --rm proton-drive version

if systemctl is-enabled dothomelab-obsidian-proton-backup.timer >/dev/null 2>&1; then
  printf 'ok - Proton backup timer is enabled\n'
else
  printf 'pending - Proton backup timer is intentionally disabled until Proton login\n'
fi

if [[ -s /srv/appdata/docker/proton-drive/last-success.name ]]; then
  printf 'ok - a checksum-verified Proton backup is recorded\n'
else
  printf 'pending - no checksum-verified Proton backup is recorded yet\n'
fi

if ((failures > 0)); then
  exit 1
fi
