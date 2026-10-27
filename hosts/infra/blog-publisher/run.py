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


def run_export(changes=None):
    command = ['/usr/local/bin/node', str(HERE / 'export.mjs'), str(VAULT), str(OUTPUT)]
    if changes is not None:
        command.append('--changed-files-stdin')
    subprocess.run(command, input=json.dumps(changes) if changes is not None else None,
                   text=True, check=True, timeout=600)


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
    changes = None  # A restart performs one complete reconciliation.
    while True:
        time.sleep(0.5)
        try:
            run_export(changes)
            changes = []
        except subprocess.CalledProcessError:
            print('Blog export failed; retrying accumulated changes on the next edit', flush=True)
        while True:
            batch = events(cursor, timeout=30)
            if batch:
                cursor = batch[-1]['id']
            if relevant(batch, folder):
                selected = [event['data'] for event in batch if event['data'].get('folder') == folder]
                if changes is not None and all('filenames' in data for data in selected):
                    changes = list(set(changes).union(name for data in selected for name in data['filenames']
                                                     if not name.startswith('.')))
                else:
                    changes = None
                break


if __name__ == '__main__':
    main()
