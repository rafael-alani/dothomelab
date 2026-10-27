#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/bin:$PATH"
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$(hostname -s)" == infra ]] || { echo 'Run inside Infra CT110' >&2; exit 1; }
bash "$here/../../blog/install-node.sh"
install -d -m 0700 /var/lib/dothomelab-blog-publisher /srv/appdata/docker/staging/blog/editorial
runtime=/var/lib/dothomelab-blog-publisher
changed=false
cmp -s "$here/package-lock.json" "$runtime/package-lock.json" || changed=true
install -m 0644 "$here/export.mjs" "$here/package.json" "$here/package-lock.json" "$here/run.py" "$runtime/"
if "$changed" || [[ ! -d "$runtime/node_modules" ]]; then
  npm ci --prefix "$runtime" --omit=dev --no-audit --no-fund
fi
systemctl disable --now dothomelab-blog-publisher.timer 2>/dev/null || true
systemctl stop dothomelab-blog-publisher.service
install -m 0644 "$here/dothomelab-blog-publisher.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dothomelab-blog-publisher.service
