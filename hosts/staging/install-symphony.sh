#!/usr/bin/env bash
# PVE-only. Source archive and public client key are appdata recovery inputs.
set -Eeuo pipefail
[[ $EUID == 0 && $(hostname -s) == afa ]] || exit 1
readonly here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
read -r revision checksum < <(python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r["commit"],r["archive_sha256"])' "$here/symphony-release.json")
[[ $revision =~ ^[a-f0-9]{40}$ && $checksum =~ ^[a-f0-9]{64}$ ]] || exit 1
readonly control=/srv/appdata/docker/symphony-staging-control
readonly archive="$control/source-$revision.tar"
[[ -f $archive && -f $control/client.pub ]] || { echo 'Restore Symphony staging source archive and client.pub from canonical appdata first' >&2; exit 1; }
printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check -
readonly source="/opt/symphony-staging/source-$revision"
install -d -m 0755 "$source"
tar -xf "$archive" -C "$source"
install -m 0755 "$source/packaging/staging/gateway.py" /opt/symphony-staging/gateway.py
pct exec 110 -- install -d -m 0755 /opt/symphony-staging
pct push 110 "$source/packaging/staging/routes.py" /opt/symphony-staging/routes.py --perms 0755
pct exec 114 -- install -d -m 0755 "$source"
pct push 114 "$archive" /tmp/symphony-source.tar --perms 0644
pct exec 114 -- tar -xf /tmp/symphony-source.tar -C "$source"
pct exec 114 -- bash "$source/packaging/staging/install-guest.sh" "$source"
# Preserve every existing key; only append this restricted application identity.
python3 - "$control/client.pub" <<'PY'
import pathlib,re,sys
pub=pathlib.Path(sys.argv[1]).read_text().strip()
if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+ symphony-staging-only',pub):
    raise ValueError('Unexpected staging public key')
line='restrict,from="192.168.0.126",command="/opt/symphony-staging/gateway.py" '+pub
path=pathlib.Path('/root/.ssh/authorized_keys')
text=path.read_text()
if pub.split()[1] not in text:
    with path.open('a') as out:
        out.write('\n'+line+'\n')
PY
# Recreate exact private routes after a clean guest restore.
python3 - <<'PY'
import importlib.util,json,pathlib
spec=importlib.util.spec_from_file_location('gateway','/opt/symphony-staging/gateway.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
path=pathlib.Path('/srv/appdata/docker/symphony-staging-control/routes.json')
if path.exists():
    for repo, route in json.loads(path.read_text()).items():
        module.routes({'repository':repo,**route},force=True)
PY
printf '%s\n' "$revision" >/opt/symphony-staging/DEPLOYED_COMMIT
pct exec 114 -- sh -c 'printf "%s\n" "$1" >/opt/symphony-staging/DEPLOYED_COMMIT' sh "$revision"
