#!/usr/bin/env bash
# PVE-only credential entry and explicit DNS cutover/rollback.
set -Eeuo pipefail
[[ $EUID == 0 && -d /etc/pve ]] || { echo 'Run on PVE as root'; exit 1; }
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$here/../../common/load-env.sh"
load_dothomelab_env /root/.env
exec python3 "$here/configure.py" "$@"
