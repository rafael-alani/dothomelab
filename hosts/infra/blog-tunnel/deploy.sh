#!/usr/bin/env bash
# PVE: isolated immutable release; does not replace CT110's shared source archive.
set -Eeuo pipefail
[[ $EUID == 0 && -d /etc/pve ]] || { echo 'Run on PVE as root'; exit 1; }
commit="$(git rev-parse "${1:-HEAD}^{commit}")"
release="/opt/dothomelab-blog-tunnel/releases/$commit"
if [[ ! -e "$release" ]]; then
  install -d -m 0755 "$release"
  git archive "$commit" | tar -xf - -C "$release"
  printf '%s\n' "$commit" >"$release/DEPLOYED_COMMIT"
fi
[[ "$(cat "$release/DEPLOYED_COMMIT")" == "$commit" ]]
if [[ "${2:-}" == --archive-only ]]; then printf '%s\n' "$release"; exit 0; fi
bash "$release/hosts/infra/blog-tunnel/manage.sh" check
source "$release/hosts/common/load-env.sh"
load_dothomelab_env /root/.env
temporary="$(mktemp -d /run/blog-tunnel-deploy.XXXXXX)"
cleanup() {
  pct exec 110 -- rm -f "$temporary/env" "$temporary/source.tar" >/dev/null 2>&1 || true
  pct exec 110 -- rmdir "$temporary" >/dev/null 2>&1 || true
  rm -f "$temporary/env" "$temporary/source.tar"
  rmdir "$temporary"
}
trap cleanup EXIT
umask 077
printf 'CLOUDFLARE_BLOG_TUNNEL_TOKEN=%s\n' "$CLOUDFLARE_BLOG_TUNNEL_TOKEN" >"$temporary/env"
tar -cf "$temporary/source.tar" -C "$release" hosts/infra/blog-tunnel hosts/common DEPLOYED_COMMIT
pct exec 110 -- mkdir -p "$release" "$temporary"
pct push 110 "$temporary/env" "$temporary/env" --perms 0600
pct push 110 "$temporary/source.tar" "$temporary/source.tar" --perms 0600
pct exec 110 -- tar -xf "$temporary/source.tar" -C "$release"
compose=(docker compose --env-file "$temporary/env" -f "$release/hosts/infra/blog-tunnel/compose.yaml")
pct exec 110 -- "${compose[@]}" config --quiet
pct exec 110 -- "${compose[@]}" pull
pct exec 110 -- "${compose[@]}" up -d --wait --wait-timeout 90
ln -sfn "$release" /opt/dothomelab-blog-tunnel/current
pct exec 110 -- ln -sfn "$release" /opt/dothomelab-blog-tunnel/current
printf 'Installed blog tunnel revision %s\n' "$commit"
