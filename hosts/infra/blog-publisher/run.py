#!/usr/bin/env python3
"""Run inside CT110. Check sync readiness without logging the API credential."""
import fcntl
import json
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUTPUT = Path('/srv/appdata/docker/staging/blog/editorial')
VAULT = Path('/vault/shared/media/obsidian')


def main():
    if not (VAULT / '.stfolder').exists() or not (VAULT / 'Blog').is_dir():
        raise RuntimeError('Synced Blog folder is not ready; retaining the current preview')
    with (OUTPUT / 'export.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        config = ET.parse('/srv/appdata/docker/syncthing/config/config.xml').getroot()
        folders = [f for f in config.findall('folder') if f.get('path') == str(VAULT)]
        if len(folders) != 1 or folders[0].get('paused') == 'true':
            raise RuntimeError('Obsidian sync folder is absent or paused')
        request = urllib.request.Request('http://127.0.0.1:8384/rest/db/status?' +
                                         urllib.parse.urlencode({'folder': folders[0].get('id')}),
                                         headers={'X-API-Key': config.findtext('gui/apikey')})
        with urllib.request.urlopen(request, timeout=10) as response:
            status = json.load(response)
        if status.get('state') != 'idle' or status.get('needTotalItems', 1) or status.get('errors', 0):
            raise RuntimeError('Obsidian synchronization is incomplete; retrying on the next timer run')
        compose = ['docker', 'compose', '-f', str(HERE / 'compose.yaml')]
        subprocess.run([*compose, 'config', '--quiet'], check=True)
        subprocess.run([*compose, 'run', '--rm', '--no-deps', 'export'], check=True, timeout=240)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # HTTP/subprocess errors must not serialize configuration or source notes.
        print(f'Blog publisher: {error if isinstance(error, RuntimeError) else type(error).__name__}')
        raise SystemExit(1)
