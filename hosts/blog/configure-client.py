#!/usr/bin/env python3
"""Reduce the selected local Syncthing vault's watcher delay to one second."""
import argparse
import json
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config', type=Path, default=Path.home() / 'Library/Application Support/Syncthing/config.xml')
parser.add_argument('--vault', type=Path, required=True)
args = parser.parse_args()
config = ET.parse(args.config).getroot()
folder = next(f.get('id') for f in config.findall('folder') if Path(f.get('path')).resolve() == args.vault.resolve())
url = 'http://' + config.findtext('gui/address') + '/rest/config/folders/' + urllib.parse.quote(folder)
headers = {'X-API-Key': config.findtext('gui/apikey')}
with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as response:
    before = json.load(response)
request = urllib.request.Request(url, data=json.dumps({'fsWatcherEnabled': True, 'fsWatcherDelayS': 1}).encode(),
                                 headers={**headers, 'Content-Type': 'application/json'}, method='PATCH')
with urllib.request.urlopen(request, timeout=10):
    pass
with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as response:
    after = json.load(response)
print(json.dumps({'folder': folder, 'previousDelaySeconds': before['fsWatcherDelayS'],
                  'delaySeconds': after['fsWatcherDelayS'], 'watcherEnabled': after['fsWatcherEnabled']}))
