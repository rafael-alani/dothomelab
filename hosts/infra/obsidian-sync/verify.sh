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
check "photos source exists" test -d /vault/shared/media/photos
check "Proton work directory exists" test -d /vault/shared/.proton-backup-work
check "Proton work directory is private" test \
  "$(stat -c %a /vault/shared/.proton-backup-work)" = 700
check "Syncthing mount is read-write" bash -c \
  "docker inspect syncthing --format '{{range .Mounts}}{{if eq .Destination \"/vault\"}}{{.RW}}{{end}}{{end}}' | grep -qx true"
check "Proton Obsidian mount is read-only" bash -c \
  "docker compose -f '$compose_file' --profile proton config | grep -A6 'source: /vault/shared/media/obsidian' | grep -q 'read_only: true'"
check "Proton photos mount is read-only" bash -c \
  "docker compose -f '$compose_file' --profile proton config | grep -A6 'source: /vault/shared/media/photos' | grep -q 'read_only: true'"
check "Proton work mount is read-write" bash -c \
  "! docker compose -f '$compose_file' --profile proton config | grep -A6 'source: /vault/shared/.proton-backup-work' | grep -q 'read_only: true'"
check "Infra Proton runner is installed" test -x \
  /usr/local/sbin/dothomelab-proton-backup-runner
check "legacy guest Proton timer is not enabled" bash -c \
  "! systemctl is-enabled dothomelab-obsidian-proton-backup.timer >/dev/null 2>&1"
check "Proton CLI image is runnable" docker compose -f "$compose_file" \
  --profile proton run --rm proton-drive version

for dataset in obsidian photos environment; do
  if [[ -s "/srv/appdata/docker/proton-drive/sources/$dataset/last-success.name" ]]; then
    printf 'ok - %s has a checksum-verified Proton generation\n' "$dataset"
  else
    printf 'pending - %s has no checksum-verified Proton generation\n' "$dataset"
  fi
done

if ((failures > 0)); then
  exit 1
fi
