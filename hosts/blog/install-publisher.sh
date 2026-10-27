#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ -d /etc/pve ]] || { echo 'Run on PVE'; exit 1; }
install -d -m 0755 /usr/local/lib/dothomelab-blog
install -m 0644 "$here/publish.py" "$here/content.py" /usr/local/lib/dothomelab-blog/
install -m 0644 "$here/dothomelab-blog-publish.path" "$here/dothomelab-blog-publish.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dothomelab-blog-publish.path
systemctl enable dothomelab-blog-publish.service
systemctl start --no-block dothomelab-blog-publish.service
