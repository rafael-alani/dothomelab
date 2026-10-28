#!/usr/bin/env bash
# Generate private review inputs without replacing the live exporter or its output.
set -euo pipefail
export PATH="/usr/local/bin:$PATH"
[[ "$(hostname -s)" == infra ]] || { echo 'Run inside Infra CT110' >&2; exit 1; }
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
runtime=/var/lib/dothomelab-blog-publisher-review
output=/srv/appdata/docker/staging/blog/review-editorial
install -d -m 0700 "$runtime" "$output"
exec 9>"$runtime/export.lock"
flock --nonblock 9 || { echo 'Another review export is running' >&2; exit 1; }
changed=false
cmp -s "$here/package-lock.json" "$runtime/package-lock.json" || changed=true
install -m 0644 "$here/export.mjs" "$here/package.json" "$here/package-lock.json" "$runtime/"
if "$changed" || [[ ! -d "$runtime/node_modules" ]]; then
  npm ci --prefix "$runtime" --omit=dev --no-audit --no-fund
fi
node "$runtime/export.mjs" /vault/shared/media/obsidian "$output"
