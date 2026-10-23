#!/usr/bin/env bash
set -Eeuo pipefail
pct exec 112 -- bash -euc '
  source_root=/opt/dothomelab-blog-observability/current
  if [[ ! -d "$source_root" ]]; then source_root=/opt/dothomelab; fi
  exec bash "$source_root/hosts/staging/blog-observability/backup-database.sh"
'
