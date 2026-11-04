#!/usr/bin/env bash
# PVE: activate the queue worker after the restricted archive and speech API.
set -Eeuo pipefail
[[ $EUID == 0 && -d /etc/pve ]]
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
revision=${1:?Pass the committed release revision}
[[ $revision =~ ^[0-9a-f]{40}$ ]]
release=/usr/local/lib/dothomelab-reference-media/releases/$revision
[[ -f $release/transcribe.py ]]
python3 - "$source_dir" <<'PY'
import json,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).parents[1]/'common'))
from dotenv import parse
os.umask(0o077)
key=dict(parse(Path('/root/.env')))['SPEECH_API_KEY']
target=Path('/srv/appdata/docker/speech/reference-client.json')
target.write_text(json.dumps({'url':'http://192.168.0.110:8092/v1','key':key}))
target.chmod(0o600)
PY
cat > /etc/systemd/system/dothomelab-reference-transcribe.service <<UNIT
[Unit]
Description=Enrich archived reference videos through the local speech API
After=network-online.target
RequiresMountsFor=/vault/shared /srv/appdata/docker
[Service]
Type=oneshot
User=reference-ingest
Group=reference-ingest
UMask=0077
LoadCredential=speech.json:/srv/appdata/docker/speech/reference-client.json
ExecStart=/usr/bin/python3 $release/transcribe.py
TimeoutStartSec=3h
Nice=10
MemoryMax=192M
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/srv/appdata/docker/reference-media
ReadOnlyPaths=/vault/shared/media/references
UNIT
cat > /etc/systemd/system/dothomelab-reference-transcribe.timer <<'UNIT'
[Unit]
Description=Discover newly archived videos and retry speech enrichment
[Timer]
OnBootSec=2min
OnUnitInactiveSec=60s
Persistent=true
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now dothomelab-reference-transcribe.timer
echo 'Transcript worker installed; source credentials stay in the collector'
