#!/usr/bin/env python3
"""PVE: fan out completed exports to the native staging and production builders."""
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from content import published_input

ROOT = Path('/srv/appdata/docker')


def publish():
    with open('/run/lock/dothomelab-blog-publish.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        while True:
            started = time.monotonic()
            source_root = ROOT / 'staging/blog/editorial'
            exported = json.loads((source_root / 'current.json').read_text())
            source = source_root / exported['revision']
            environments = [('staging', 114)]
            if (ROOT / 'production/blog/current.json').exists():
                environments.append(('production', 115))
            if ('production', 115) in environments:
                destination = ROOT / 'production/blog/editorial'
                revision = published_input(source, destination, owner=(100000, 100000))
                marker = destination / 'current.next'
                marker.write_text(json.dumps({**exported, 'revision': revision, 'source_revision': source.name}) + '\n')
                os.chown(marker, 100000, 100000)
                marker.chmod(0o600)
                marker.replace(destination / 'current.json')
            def build(environment, guest):
                subprocess.run(['pct', 'exec', str(guest), '--', 'python3',
                                '/opt/dothomelab/hosts/blog/build.py', '--environment', environment], check=True)
                subprocess.run(['pct', 'exec', str(guest), '--', 'systemctl', 'start', 'dothomelab-blog-web.service'], check=True)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(build, environment, guest)
                           for environment, guest in environments]
                errors = [error for future in futures if (error := future.exception())]
            print(json.dumps({'export': source.name, 'publishSeconds': round(time.monotonic() - started, 3), 'failures': len(errors)}), flush=True)
            if json.loads((source_root / 'current.json').read_text())['revision'] == source.name:
                if errors:
                    raise RuntimeError('A blog build failed; see its stage output')
                return


if __name__ == '__main__':
    if not Path('/etc/pve').is_dir():
        raise SystemExit('Run on PVE')
    publish()
