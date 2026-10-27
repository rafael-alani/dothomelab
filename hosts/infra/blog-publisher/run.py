#!/usr/bin/env python3
"""CT110: export on Syncthing index changes, without polling deployments."""
import json
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUTPUT = Path('/srv/appdata/docker/staging/blog/editorial')
VAULT = Path('/vault/shared/media/obsidian')


def run_export():
    subprocess.run(['/usr/local/bin/node', str(HERE / 'export.mjs'), str(VAULT), str(OUTPUT)],
                   check=True, timeout=600)


def relevant(batch, folder):
    return any(event['data'].get('folder') == folder and any(
        not name.startswith('.') for name in event['data'].get('filenames', ['Blog/']))
        for event in batch)


def main():
    config = ET.parse('/srv/appdata/docker/syncthing/config/config.xml').getroot()
    folder = next(f.get('id') for f in config.findall('folder') if f.get('path') == str(VAULT))
    key = config.findtext('gui/apikey')
    def events(since, **options):
        query = urllib.parse.urlencode({'events': 'LocalIndexUpdated', 'since': since, **options})
        request = urllib.request.Request('http://127.0.0.1:8384/rest/events?' + query,
                                         headers={'X-API-Key': key})
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.load(response)
    latest = events(0, limit=1, timeout=1)
    cursor = latest[-1]['id'] if latest else 0
    pending = True
    while True:
        if pending:
            time.sleep(0.5)
            try:
                run_export()
            except subprocess.CalledProcessError:
                print('Blog export failed; retaining the served files until the next edit', flush=True)
            pending = False
        batch = events(cursor, timeout=30)
        if batch:
            cursor = batch[-1]['id']
            pending = relevant(batch, folder)


if __name__ == '__main__':
    main()
