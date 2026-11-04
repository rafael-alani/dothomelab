#!/usr/bin/env python3
"""Request or export selected cached video transcripts through the scoped archive key."""
import argparse
import json
import os
from pathlib import Path
from transport import Transport
from instagram import atomic_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--support', type=Path, required=True)
    p.add_argument('--source-key', action='append', required=True)
    p.add_argument('--output', type=Path)
    p.add_argument('--request', action='store_true')
    a = p.parse_args()
    os.umask(0o077)
    config = json.loads((a.support / 'config.json').read_text())
    transport = Transport(config['host'], a.support / 'ingest-key')
    catalog = transport.request({'action': 'catalog'})
    selection = []
    for key in dict.fromkeys(a.source_key):
        assets = [x for x in catalog['assets'] if any(o['source_key'] == key for o in x['origins']) and x['path'].endswith(('.mp4','.mov','.webm'))]
        if not assets:
            raise SystemExit('Selected video is not archived: ' + key)
        selection.extend(x for x in assets if x not in selection)
    rows = transport.request({'action': 'request_transcripts' if a.request else 'transcripts', 'asset_ids': [x['id'] for x in selection]})
    print(json.dumps({'selected':len(selection), 'statuses':[r['status'] for r in rows]}))
    if a.output:
        if any(r['status'] != 'ready' for r in rows):
            raise SystemExit('All selected transcripts must be ready before export')
        a.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(a.output, {'schema':1,'assets':selection,'transcripts':rows})
        print('Exported private context:', a.output)


if __name__ == '__main__':
    main()
