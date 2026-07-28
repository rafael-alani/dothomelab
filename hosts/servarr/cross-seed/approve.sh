#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" != "--manual-tests-passed" || $# -ne 1 ]]; then
  echo "Usage: $0 --manual-tests-passed" >&2
  echo "Run this only after all three Prowlarr UI tests pass and the indexers are enabled." >&2
  exit 2
fi

: "${DOTHOMELAB_ENV:=/run/dothomelab.env}"
# shellcheck disable=SC1091
source /opt/dothomelab/hosts/common/load-env.sh
load_dothomelab_env "$DOTHOMELAB_ENV"

/opt/dothomelab/hosts/servarr/cross-seed/configure.py --approve
exec /opt/dothomelab/hosts/servarr/cross-seed/deploy.sh
