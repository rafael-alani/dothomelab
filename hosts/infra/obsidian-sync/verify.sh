#!/usr/bin/env bash
set -euo pipefail

compose_file="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/compose.yaml"
proton_runtime=/usr/local/lib/dothomelab-proton-backup/current
proton_compose_file="$proton_runtime/compose.yaml"
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
check "Syncthing is enrolled in backup-gated WUD" bash -c \
  "test \"\$(docker inspect syncthing --format '{{index .Config.Labels \"wud.watch\"}} {{index .Config.Labels \"wud.watch.digest\"}} {{index .Config.Labels \"wud.trigger.include\"}}')\" = 'true true docker.backupgated'"
check "GUI listens only on loopback" bash -c \
  "ss -lnt | awk '{print \$4}' | grep -qx '127.0.0.1:8384'"
check "GUI has static bcrypt authentication" python3 - <<'PY'
import re
import xml.etree.ElementTree as ET

gui = ET.parse(
    "/srv/appdata/docker/syncthing/config/config.xml"
).getroot().find("./gui")
if gui is None:
    raise SystemExit(1)
username = (gui.findtext("user") or "").strip()
password = (gui.findtext("password") or "").strip()
insecure_admin = (gui.findtext("insecureAdminAccess") or "false").lower()
skip_host_check = (gui.findtext("insecureSkipHostcheck") or "false").lower()
valid_hash = re.fullmatch(r"\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}", password)
raise SystemExit(
    0
    if username
    and valid_hash
    and insecure_admin == "false"
    and skip_host_check == "true"
    else 1
)
PY
check "Obsidian folder uses canonical shared paths" python3 - <<'PY'
import json
import urllib.request
import xml.etree.ElementTree as ET

root = ET.parse(
    "/srv/appdata/docker/syncthing/config/config.xml"
).getroot()
api_key = root.findtext("./gui/apikey")
request = urllib.request.Request(
    "http://127.0.0.1:8384/rest/config/folders",
    headers={"X-API-Key": api_key},
)
with urllib.request.urlopen(request, timeout=10) as response:
    folders = json.load(response)

matching = [
    folder
    for folder in folders
    if folder.get("path") == "/vault/shared/media/obsidian"
]
if len(matching) != 1:
    raise SystemExit(1)
folder = matching[0]
versioning = folder.get("versioning", {})
raise SystemExit(
    0
    if folder.get("type") == "sendreceive"
    and not versioning.get("type")
    and not folder.get("paused")
    else 1
)
PY
check "Pi-hole has exact Syncthing DNS" \
  /opt/dothomelab/hosts/infra/services/configure-pihole-dns.py --check
check "private Syncthing HTTPS route responds" bash -c \
  "test \"\$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --resolve syncthing.rafael.media:443:192.168.0.110 https://syncthing.rafael.media/)\" = 200"
check "sync TCP port listens" bash -c \
  "ss -lnt | awk '{print \$4}' | grep -Eq '(^|:)22000$'"
check "vault marker exists" test -d /vault/shared/media/obsidian/.stfolder
check "photos source exists" test -d /vault/shared/media/photos
check "Proton work directory exists" test -d /vault/shared/.proton-backup-work
check "Proton work directory is private" test \
  "$(stat -c %a /vault/shared/.proton-backup-work)" = 700
check "Syncthing shared mount is canonical and read-write" bash -c \
  "docker inspect syncthing --format '{{range .Mounts}}{{if eq .Destination \"/vault/shared\"}}{{.Source}} {{.RW}}{{end}}{{end}}' | grep -qx '/vault/shared true'"
check "legacy Syncthing /vault alias is absent" bash -c \
  "! docker inspect syncthing --format '{{range .Mounts}}{{println .Destination}}{{end}}' | grep -qx /vault"
check "Proton Obsidian mount is read-only" bash -c \
  "docker compose --env-file /dev/null -f '$proton_compose_file' --profile proton config | grep -A6 'source: /vault/shared/media/obsidian' | grep -q 'target: /vault/shared/media/obsidian' && docker compose --env-file /dev/null -f '$proton_compose_file' --profile proton config | grep -A6 'source: /vault/shared/media/obsidian' | grep -q 'read_only: true'"
check "Proton photos mount is read-only" bash -c \
  "docker compose --env-file /dev/null -f '$proton_compose_file' --profile proton config | grep -A6 'source: /vault/shared/media/photos' | grep -q 'target: /vault/shared/media/photos' && docker compose --env-file /dev/null -f '$proton_compose_file' --profile proton config | grep -A6 'source: /vault/shared/media/photos' | grep -q 'read_only: true'"
check "Immich originals source exists" test -d /srv/appdata/docker/immich/upload/upload
check "Immich organized originals source exists" test -d /srv/appdata/docker/immich/upload/library
check "Proton work mount is read-write" bash -c \
  "! docker compose --env-file /dev/null -f '$proton_compose_file' --profile proton config | grep -A6 'source: /vault/shared/.proton-backup-work' | grep -q 'read_only: true'"
check "Protected Proton runtime passes readiness" \
  "$proton_runtime/backup-runner.sh" --check
check "legacy guest Proton timer is not enabled" bash -c \
  "! systemctl is-enabled dothomelab-obsidian-proton-backup.timer >/dev/null 2>&1"
check "Proton image uses and sees canonical source paths" \
  docker compose --env-file /dev/null -f "$proton_compose_file" --profile proton run --rm --no-build \
  --entrypoint /bin/sh proton-drive -ec \
  'grep -Fq "/vault/shared/media/obsidian" /usr/local/bin/proton-backup
  grep -Fq "/vault/shared/media/photos" /usr/local/bin/proton-backup
  test -d /vault/shared/media/obsidian
  test -d /vault/shared/media/photos'
check "Proton CLI image is runnable" docker compose --env-file /dev/null -f "$proton_compose_file" \
  --profile proton run --rm --no-build proton-drive version

for dataset in obsidian photos immich environment; do
  if [[ -s "/srv/appdata/docker/proton-drive/sources/$dataset/last-success.name" ]]; then
    printf 'ok - %s has a checksum-verified Proton generation\n' "$dataset"
  else
    printf 'pending - %s has no checksum-verified Proton generation\n' "$dataset"
  fi
done

if ((failures > 0)); then
  exit 1
fi
