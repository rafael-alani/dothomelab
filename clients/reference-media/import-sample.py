#!/usr/bin/env python3
"""Import a bounded real sample through the durable archive; retain failed work."""
import argparse
import json
import os
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from collector import open_browser
from downloader import download
from transport import Transport
from worker import thumbnail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support', type=Path, required=True)
    parser.add_argument('--host', required=True)
    parser.add_argument('--limit', type=int, default=25)
    args = parser.parse_args()
    os.umask(0o077)
    transport = Transport(args.host, args.support / 'ingest-key')
    transport.request({'action': 'status'})
    document = json.loads((args.support / 'yaay-inventory.json').read_text())
    transport.inventory(document)
    items = {item['source_key']: item for item in document['items'] if item.get('url', '').startswith('https://www.instagram.com/')}
    # Mix multi-place/carousel and unfiled saves; download identities only once.
    selected = sorted(items.values(), key=lambda item: (-int(len(item['metadata'].get('carousel_members', [])) > 1), -int(len(item['metadata'].get('places', [])) > 1)))[:args.limit]
    completed, failed = 0, 0
    with sync_playwright() as p:
        browser = open_browser(p, args.support / 'browser-profile')
        cookies = browser.cookies('https://www.instagram.com/')
        for item in selected:
            previous = [f.parent for f in args.support.glob('download-*/failure.json') if json.loads(f.read_text()).get('source_key') == item['source_key']]
            temporary = previous[0] if previous else Path(tempfile.mkdtemp(prefix='download-', dir=args.support))
            try:
                files = download(item['url'], cookies, temporary)
                receipt = []
                for member in files:
                    asset = transport.put(member['file'])
                    transport.request({'action': 'link', 'source_key': item['source_key'], 'ordinal': member['ordinal'], 'asset_id': asset['id']})
                    receipt.append({'id': asset['id'], 'ordinal': member['ordinal']})
                    thumbnail(member['file'], Path(json.loads((args.support / 'config.json').read_text())['vault']) / 'References/Thumbnails' / (asset['id'] + '.jpg'))
                transport.request({'action': 'complete_post', 'source_key': item['source_key'], 'assets': receipt})
                for member in files:
                    member['file'].unlink()  # Verified acknowledgement, never a canonical file.
                if (temporary / 'failure.json').exists():
                    (temporary / 'failure.json').unlink()
                temporary.rmdir()
                completed += 1
            except Exception as error:
                failed += 1
                if type(error) is RuntimeError and str(error).startswith('source_download_incomplete:'):
                    print(str(error), flush=True)
                # No raw exception messages: downloader failures can include tokens.
                (temporary / 'failure.json').write_text(json.dumps({'source_key': item['source_key'], 'error': type(error).__name__}))
            print(json.dumps({'completed_posts': completed, 'failed_posts': failed, 'target': len(selected)}), flush=True)
            if failed >= 2 and completed == 0:
                break  # Authentication/rate failure is not a reason to hammer 25 posts.
        browser.close()
    print(json.dumps(transport.request({'action': 'status'})))


if __name__ == '__main__':
    main()
