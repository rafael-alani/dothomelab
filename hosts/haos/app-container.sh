#!/usr/bin/env bash
# Supervisor renamed addon_<slug> containers to app_<slug> in 2026.
ha_app_container() {
  local slug="$1"
  [[ "$slug" =~ ^[a-z0-9_]+$ ]] || return 1
  qm guest exec "$HAOS_VMID" -- docker ps --format '{{.Names}}' |
    python3 -c '
import json, sys
result = json.load(sys.stdin)
if result.get("exitcode", 1):
    raise SystemExit("Cannot inspect Home Assistant app containers")
matches = [name for name in result.get("out-data", "").splitlines()
           if name in ("app_" + sys.argv[1], "addon_" + sys.argv[1])]
if len(matches) != 1:
    raise SystemExit("Expected exactly one running Home Assistant app: " + sys.argv[1])
print(matches[0])
' "$slug"
}
