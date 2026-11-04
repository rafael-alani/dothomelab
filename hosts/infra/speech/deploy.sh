#!/usr/bin/env bash
# PVE: deploy a committed, isolated source release without replacing guest sources.
set -Eeuo pipefail
[[ $EUID == 0 && -d /etc/pve ]] || { echo 'Run on PVE as root'; exit 1; }
revision=$(git rev-parse "${1:-HEAD}^{commit}")
release=/opt/dothomelab-speech/releases/$revision
if [[ ! -e $release ]]; then
  install -d -m 0755 "$release"
  git archive "$revision" | tar -xf - -C "$release"
  printf '%s\n' "$revision" > "$release/DEPLOYED_COMMIT"
fi
python3 "$release/hosts/infra/speech/initialize.py"
transport=$(mktemp -d /run/speech-deploy.XXXXXX)
cleanup() {
  pct exec 110 -- rm -f "$transport/source.tar" >/dev/null 2>&1 || true
  pct exec 110 -- rmdir "$transport" >/dev/null 2>&1 || true
  rm -f "$transport/source.tar"
  rmdir "$transport"
}
trap cleanup EXIT
tar -cf "$transport/source.tar" -C "$release" hosts/infra/speech hosts/infra/observability/targets.json hosts/common DEPLOYED_COMMIT
pct exec 110 -- mkdir -p "$release" "$transport"
pct push 110 "$transport/source.tar" "$transport/source.tar" --perms 0600
pct exec 110 -- tar -xf "$transport/source.tar" -C "$release"
pct exec 110 -- bash "$release/hosts/infra/speech/prepare.sh"
compose=(docker compose --env-file /srv/appdata/docker/speech/runtime.env -f "$release/hosts/infra/speech/compose.yaml")
pct exec 110 -- "${compose[@]}" config --quiet
pct exec 110 -- "${compose[@]}" pull
pct exec 110 -- "${compose[@]}" up -d --wait --wait-timeout 180
ln -sfn "$release" /opt/dothomelab-speech/current
pct exec 110 -- ln -sfn "$release" /opt/dothomelab-speech/current
pct exec 110 -- python3 "$release/hosts/infra/speech/install-model.py"
pct exec 110 -- python3 "$release/hosts/infra/speech/enroll-monitoring.py"
printf 'Speech API installed at revision %s\n' "$revision"
