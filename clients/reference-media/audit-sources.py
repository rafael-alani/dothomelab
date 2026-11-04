#!/usr/bin/env python3
"""Fresh authenticated source observations, without archive or vault writes.

Uses the collector lock/profile and existing collectors. The output directory
must be new and private; it holds sanitized inventories and pagination evidence.
"""
import argparse
import fcntl
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

import collector
import instagram
from playwright.sync_api import sync_playwright


def cursor_digest(value):
    return None if value is None else hashlib.sha256(str(value).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', choices=('instagram', 'yaay'), action='append')
    parser.add_argument('--post', action='append', default=[], help='Instagram original URL to inspect without downloading')
    parser.add_argument('--hash-yaay-post', action='append', default=[], help='Read saved-copy media into memory and record hashes; no files/uploads')
    parser.add_argument('--yaay-ui', action='store_true', help='Inspect every rendered board and section order')
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    evidence = {'started': time.time(), 'instagram_pages': [], 'yaay_pages': [], 'errors': {}}

    def save():
        instagram.atomic_json(args.output / 'pagination.json', evidence)

    original_find = instagram.extractor.find

    def find(url):
        ext = original_find(url)
        if ext is None:
            return ext
        initialize = ext.initialize

        def init():
            result = initialize()
            call = ext.api._call

            def observed_call(endpoint, **kwargs):
                result = call(endpoint, **kwargs)
                posts = [row.get('media', row) for row in result.get('items', [])]
                evidence['instagram_pages'].append({
                    'endpoint': endpoint, 'checked_at': time.time(),
                    'input_cursor_sha256': cursor_digest((kwargs.get('params') or {}).get('max_id')),
                    'next_cursor_sha256': cursor_digest(result.get('next_max_id')),
                    'more_available': result.get('more_available'), 'status': result.get('status'),
                    'posts': [{'id': str(p['pk']), 'source_key': 'instagram:' + p['code'],
                               'members': instagram.normalize(p)['metadata']['carousel_members']}
                              for p in posts if 'pk' in p and 'code' in p]})
                save()
                return result

            ext.api._call = observed_call
            return result

        ext.initialize = init
        return ext

    instagram.extractor.find = find
    original_response = collector.YaayCapture.response
    original_init = collector.YaayCapture.__init__
    captures = []

    def observed_init(self):
        original_init(self)
        captures.append(self)

    def observed_response(self, res):
        before = dict(self.pages)
        original_response(self, res)
        if self.pages == before:
            return  # Ignore incremental/noninventory responses and UI teardown.
        parsed = urlsplit(res.url)
        if parsed.hostname != 'yaaytravel.com' or parsed.path != '/graphql':
            return
        try:
            payload, requests = res.json(), res.request.post_data_json
            for row, query in zip(payload if isinstance(payload, list) else [payload],
                                  requests if isinstance(requests, list) else [requests], strict=True):
                for source in ('board', 'saved'):
                    update = (row.get('data') or {}).get(source, {}).get('updates')
                    if update is None:
                        continue
                    variables = query.get('variables') or {}
                    evidence['yaay_pages'].append({
                        'feed': source, 'checked_at': time.time(), 'http': res.status,
                        'initial_checkpoint': variables.get('checkpoint') is None,
                        'include': variables.get('filter', {}).get('include'),
                        'input_cursor_sha256': cursor_digest(variables.get('after')),
                        'next_cursor_sha256': cursor_digest(update['pageInfo'].get('endCursor')),
                        'more_available': update['pageInfo']['hasNextPage'],
                        'ids': [edge['node']['id'] for edge in update['edges']]})
                    save()
        except Exception as error:
            evidence['errors']['yaay_page_capture'] = type(error).__name__
            save()

    collector.YaayCapture.response = observed_response
    collector.YaayCapture.__init__ = observed_init
    with (args.support / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = json.loads((args.support / 'config.json').read_text())
        with sync_playwright() as playwright:
            browser = collector.open_browser(playwright, args.support / 'browser-profile')
            context = collector.fresh_context(browser)
            try:
                for source in args.source or ('yaay', 'instagram'):
                    print(json.dumps({'source': source, 'phase': 'scanning'}), flush=True)
                    try:
                        if source == 'yaay':
                            document, media = collector.collect_yaay(context)
                            instagram.atomic_json(args.output / 'yaay-observed.json', document)
                            instagram.atomic_json(args.output / 'yaay-media-kinds.json', {
                                key: [{'ordinal': m['ordinal'], 'kind': m['kind'], 'url_present': bool(m['url'])}
                                      for m in members] for key, members in media.items()})
                            for key in args.hash_yaay_post:
                                hashes = []
                                for member in media.get(key, []):
                                    row = {'ordinal': member['ordinal'], 'kind': member['kind']}
                                    parsed = urlsplit(member['url'] or '')
                                    if parsed.scheme == 'https' and parsed.hostname and parsed.hostname not in {'localhost', '127.0.0.1'}:
                                        response = context.request.get(member['url'], timeout=60000)
                                        try:
                                            row['http'] = response.status
                                            if response.ok:
                                                body = response.body()
                                                row.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                                                           jpeg=body.startswith(b'\xff\xd8\xff'), mp4=body[4:8] == b'ftyp')
                                        finally:
                                            response.dispose()
                                    else:
                                        row['error'] = 'missing_transport_url'
                                    hashes.append(row)
                                instagram.atomic_json(args.output / ('saved-copy-' + hashlib.sha256(key.encode()).hexdigest()[:16] + '.json'),
                                                      {'source_key': key, 'members': hashes})
                            if args.yaay_ui:
                                from audit_yaay_ui import inspect_boards, inspect_saved
                                inspect_boards(context, captures[-1], document, args.output / 'yaay-ui-boards.json')
                                inspect_saved(context, captures[-1], document, args.output / 'yaay-ui-saved.json')
                        else:
                            document = instagram.advance(context, browser.cookies('https://www.instagram.com/'),
                                config['instagram_saved_url'], args.output / 'instagram-checkpoint.json', page_budget=None)
                        instagram.atomic_json(args.output / (source + '-observed.json'), document)
                        if document['status'] != 'complete':
                            evidence['errors'][source] = 'incomplete_inventory'
                        print(json.dumps({'source': source, 'status': document['status'],
                                          'items': len(document['items']), 'collections': len(document['collections']),
                                          'gaps': document['gaps']}), flush=True)
                    except Exception as error:
                        evidence['errors'][source] = type(error).__name__
                        print(json.dumps({'source': source, 'error': type(error).__name__}), flush=True)
                    save()
                for url in args.post:
                    try:
                        instagram.configure(browser.cookies('https://www.instagram.com/'))
                        ext = original_find(url)
                        ext.initialize()
                        posts = [instagram.normalize(post) for post in ext.posts()]
                        instagram.atomic_json(args.output / ('post-' + hashlib.sha256(url.encode()).hexdigest()[:16] + '.json'), posts)
                        print(json.dumps({'original_posts': [{'source_key': p['source_key'],
                                          'members': p['metadata']['carousel_members']} for p in posts]}), flush=True)
                        ext.session.close()
                    except Exception as error:
                        evidence['errors']['original-' + hashlib.sha256(url.encode()).hexdigest()[:16]] = type(error).__name__
                    save()
            finally:
                context.close()
                browser.close()
    evidence['finished'] = time.time()
    save()
    return bool(evidence['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
