#!/usr/bin/env python3
"""Guest: add only speech's probe to the existing mounted monitoring configuration."""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

module = '''  speech_auth_boundary:
    prober: http
    timeout: 8s
    http:
      preferred_ip_protocol: ip4
      follow_redirects: false
      valid_status_codes: [403]
'''
root = Path(__file__).resolve().parents[1]
target = next(x for x in json.loads((root / 'observability/targets.json').read_text()) if x['labels']['project'] == 'speech')


def mount(container, destination):
    mounts = json.loads(subprocess.check_output(['docker','inspect',container,'--format','{{json .Mounts}}'], text=True))
    path = Path(next(m['Source'] for m in mounts if m['Destination'] == destination))
    if not path.is_file() or path.is_symlink():
        raise SystemExit('Unexpected monitoring config mount')
    return path


blackbox = mount('blackbox', '/etc/blackbox/config.yml')
targets = mount('prometheus', '/etc/prometheus/targets.json')
old_blackbox, old_targets = blackbox.read_text(), targets.read_text()
rows = json.loads(old_targets)
rows = [r for r in rows if r.get('labels',{}).get('project') != 'speech'] + [target]
updated = old_blackbox if '  speech_auth_boundary:' in old_blackbox else old_blackbox.replace('modules:\n', 'modules:\n' + module, 1)
if '  speech_auth_boundary:' not in updated:
    raise SystemExit('Cannot find the Blackbox modules block')
if updated == old_blackbox and json.loads(old_targets) == rows:
    print('Speech monitoring enrollment already matches')
    raise SystemExit(0)
stamp = str(time.time_ns())
for p, previous in ((blackbox,old_blackbox),(targets,old_targets)):
    p.with_name(p.name + '.before-speech-' + stamp).write_text(previous)
try:
    # These are individual bind-mounted files: preserve the inode for running containers.
    blackbox.write_text(updated)
    urllib.request.urlopen(urllib.request.Request('http://192.168.0.110:9115/-/reload',method='POST'), timeout=10).close()
    targets.write_text(json.dumps(rows,indent=2)+'\n')
except Exception:
    blackbox.write_text(old_blackbox); targets.write_text(old_targets)
    urllib.request.urlopen(urllib.request.Request('http://192.168.0.110:9115/-/reload',method='POST'), timeout=10).close()
    raise
print('Speech auth-boundary probe enrolled; existing targets retained. Rollback suffix:', stamp)
