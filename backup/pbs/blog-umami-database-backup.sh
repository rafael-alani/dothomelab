#!/usr/bin/env bash
set -Eeuo pipefail
pct exec 110 -- bash -euc '
  source_root=/opt/dothomelab-observability/current
  if [[ ! -d "$source_root" ]]; then source_root=/opt/dothomelab; fi
  exec bash "$source_root/hosts/infra/observability/backup-database.sh"
'
