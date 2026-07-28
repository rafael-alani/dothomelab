#!/usr/bin/env bash
set -Eeuo pipefail

readonly base_url="http://gluetun:8080"
readonly category="listenarr"
readonly save_path="/data/torrents/completed/listenarr"

[[ "$(docker inspect --format '{{.State.Health.Status}}' qbittorrent)" == "healthy" ]] || {
  echo "qBittorrent is not healthy" >&2
  exit 1
}

current="$(
  docker exec sonarr curl --fail --silent --show-error \
    "$base_url/api/v2/torrents/categories"
)"

action="$(
  python3 - "$category" "$save_path" "$current" <<'PY'
import json
import sys

category, save_path, payload = sys.argv[1:]
state = json.loads(payload)
if category not in state:
    print("create")
elif state[category].get("savePath") != save_path:
    print("update")
else:
    print("none")
PY
)"

case "$action" in
  create)
    docker exec sonarr curl --fail --silent --show-error \
      --data-urlencode "category=$category" \
      --data-urlencode "savePath=$save_path" \
      "$base_url/api/v2/torrents/createCategory" >/dev/null
    ;;
  update)
    docker exec sonarr curl --fail --silent --show-error \
      --data-urlencode "category=$category" \
      --data-urlencode "savePath=$save_path" \
      "$base_url/api/v2/torrents/editCategory" >/dev/null
    ;;
  none) ;;
  *)
    echo "Unexpected qBittorrent category action: $action" >&2
    exit 1
    ;;
esac

verified="$(
  docker exec sonarr curl --fail --silent --show-error \
    "$base_url/api/v2/torrents/categories"
)"
python3 - "$category" "$save_path" "$verified" <<'PY'
import json
import sys

category, save_path, payload = sys.argv[1:]
state = json.loads(payload)
if state.get(category, {}).get("savePath") != save_path:
    raise SystemExit("Listenarr qBittorrent category did not reconcile")
PY

echo "qBittorrent Listenarr category reconciled"
