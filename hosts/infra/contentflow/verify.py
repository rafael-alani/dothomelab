#!/usr/bin/env python3
"""Read-only checks of Contentflow enrollment and the n8n integration network."""
import json
from pathlib import Path
import subprocess

release = json.loads(Path(__file__).with_name('release.json').read_text())
item = json.loads(subprocess.check_output(['docker', 'inspect', 'contentflow-contentflow-1']))[0]
assert item['Image'] == release['image_id'], 'Contentflow image identity drifted'
assert item['State']['Health']['Status'] == 'healthy', 'Contentflow is not healthy'
assert item['Config']['User'] == '1000:1000'
assert item['HostConfig']['ReadonlyRootfs']
assert item['HostConfig']['PortBindings']['8787/tcp'] == [{'HostIp': '127.0.0.1', 'HostPort': '8787'}]
assert 'n8n_default' in item['NetworkSettings']['Networks']
assert 'CONTENTFLOW_PUBLISH_ENABLED=false' in item['Config']['Env']
mounts = {m['Destination']: m for m in item['Mounts']}
for dest, source, writable in [
    ('/state', '/srv/appdata/docker/contentflow/state', True),
    ('/sources/obsidian', '/vault/shared/media/obsidian', False),
    ('/sources/media', '/srv/appdata/docker/contentflow/example-media', False),
    ('/run/secrets/contentflow_token', '/srv/appdata/docker/contentflow/secrets/api-token', False),
]:
    assert mounts[dest]['Source'] == source and mounts[dest]['RW'] == writable, f'Mount drift: {dest}'
subprocess.run(['docker', 'exec', 'n8n', 'node', '-e',
                "fetch('http://contentflow:8787/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"], check=True)
print('Contentflow exact image, isolated mounts, private endpoint and n8n network health passed; publishing remains disabled')
