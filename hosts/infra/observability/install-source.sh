#!/usr/bin/env bash
# PVE: retain an immutable Git archive for the scheduled fleet export.
set -Eeuo pipefail
[[ $EUID == 0 && -d /etc/pve ]] || { echo 'Run on PVE as root'; exit 1; }
repo="$(git rev-parse --show-toplevel)"
commit="$(git rev-parse HEAD)"
[[ -z "$(git status --porcelain)" ]] || { echo 'Use a clean committed checkout'; exit 1; }
release="/opt/dothomelab-observability/releases/$commit"
if [[ ! -e "$release" ]]; then
  install -d -m 0755 "$release"
  git archive HEAD | tar -xf - -C "$release"
  printf '%s\n' "$commit" >"$release/DEPLOYED_COMMIT"
fi
[[ "$(cat "$release/DEPLOYED_COMMIT")" == "$commit" ]]
if [[ "${1:-}" == --archive-only ]]; then exit 0; fi
bash "$release/hosts/infra/observability/install-fleet.sh"
