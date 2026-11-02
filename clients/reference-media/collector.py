#!/usr/bin/env python3
"""Observe authenticated source UI; collect complete snapshots, never session logs."""
import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from inventory import yaay_document


class YaayCapture:
    def __init__(self):
        self.authenticated = False
        self.nodes = {'board': {}, 'saved': {}}
        self.complete = {'board': False, 'saved': False}
        self.pages = {'board': 0, 'saved': 0}
        self.errors = []
        self.cursor = {'board': None, 'saved': None}
        self.started = {'board': False, 'saved': False}

    def response(self, response):
        url = urlsplit(response.url)
        if url.hostname != 'yaaytravel.com' or url.path != '/graphql':
            return
        try:
            if response.status != 200:
                self.errors.append('rate_limited' if response.status == 429 else 'source_http_error')
                return
            payload = response.json()
            request = response.request.post_data_json
            for row, query in zip(payload if isinstance(payload, list) else [payload], request if isinstance(request, list) else [request], strict=True):
                if row.get('errors'):
                    self.errors.append('source_graphql_error')
                data = row.get('data') or {}
                if 'me' in data:
                    self.authenticated = data['me']['me']['authenticated'] is True
                for source in self.nodes:
                    update = data.get(source, {}).get('updates')
                    if update is None:
                        continue
                    info = update['pageInfo']
                    if not isinstance(info['hasNextPage'], bool):
                        raise ValueError('pagination_schema')
                    variables = query.get('variables') or {}
                    if variables.get('filter', {}).get('include') != 'active' or variables.get('checkpoint') is not None:
                        continue  # Incremental responses cannot certify a full scan.
                    if self.complete[source] or variables.get('after') != self.cursor[source]:
                        raise ValueError('pagination_chain_mismatch')
                    self.started[source] = True
                    self.cursor[source] = info.get('endCursor')
                    if info['hasNextPage'] and not self.cursor[source]:
                        raise ValueError('missing_next_cursor')
                    self.pages[source] += 1
                    for edge in update['edges']:
                        self.nodes[source][edge['node']['id']] = edge['node']
                    # Fresh contexts have no checkpoint/cache. The application's
                    # own paging reaches an explicit terminal page for each feed.
                    if info['hasNextPage'] is False:
                        self.complete[source] = True
        except Exception:
            self.errors.append('source_schema_or_response_error')


def collect_yaay(context, verify_ui=True):
    page = context.new_page()
    capture = YaayCapture()
    page.on('response', capture.response)
    page.goto('https://yaaytravel.com/boards/?showBottomDrawer=expanded', wait_until='domcontentloaded', timeout=60000)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and not (capture.authenticated and all(capture.complete.values())):
        if '/login' in page.url:
            raise RuntimeError('yaay_needs_sign_in')
        if capture.errors:
            break
        page.wait_for_timeout(500)
    document, transport = yaay_document(capture.nodes['board'], capture.nodes['saved'])
    document['gaps'].extend(capture.errors)
    if not capture.authenticated:
        document['gaps'].append('authentication_not_confirmed')
    if not all(capture.complete.values()):
        document['gaps'].append('pagination_incomplete')
    document['completion'] = {'authenticated': capture.authenticated,
                              'pagination_complete': all(capture.complete.values()),
                              'roots_complete': capture.complete['board'],
                              'visited_collections': len(document['collections']),
                              'pages': capture.pages, 'method': 'fresh-browser-observed-ui-sync'}
    if verify_ui and capture.authenticated and capture.complete['board']:
        # UI readiness is independent of the feed response; the drawer can mount
        # after synchronization. Verify every root represented on the page.
        if page.get_by_text('Continue to Yaay', exact=True).count():
            page.keyboard.press('Escape')
            page.get_by_text('Continue to Yaay', exact=True).click(timeout=5000)
        elif page.get_by_text('Skip intro', exact=True).count():
            page.get_by_text('Skip intro', exact=True).click()
        if not page.locator('a[href*="/boards/view/"]').count():
            page.goto('https://yaaytravel.com/boards/?showBottomDrawer=expanded', wait_until='domcontentloaded')
        try:
            page.locator('a[href*="/boards/view/"]').first.wait_for(state='attached', timeout=30000)
            links = page.locator('a[href*="/boards/view/"]').evaluate_all('(els) => els.map(e => e.getAttribute("href"))')
            from urllib.parse import parse_qs
            displayed = {parse_qs(urlsplit(link).query)['boardId'][0] for link in links}
            expected = {b['item']['id'] for b in capture.nodes['board'].values() if not b.get('deleted') and not b['item'].get('deletedAt')}
            if displayed != expected:
                document['gaps'].append('root_ui_count_mismatch')
            document['completion']['ui_boards'] = len(displayed)
            # China is the user-selected live hierarchy case. Read every section
            # and compare with stable IDs from the same authenticated UI sync.
            china = [b for b in capture.nodes['board'].values() if b['item']['title'].lower().startswith('china') and not b.get('deleted')]
            for board in china:
                identity = board['item']['id']
                link = next((link for link in links if parse_qs(urlsplit(link).query)['boardId'][0] == identity), None)
                if not link:
                    document['gaps'].append('china_board_missing_in_ui')
                    continue
                page.goto('https://yaaytravel.com' + link, wait_until='domcontentloaded')
                page.get_by_role('button', name='Add another section', exact=True).wait_for(state='attached', timeout=30000)
                headings = page.locator('h3').all_text_contents()
                groups = [g for g in board['groups'] if not g.get('deletedAt')]
                expected_titles = [g['title'] for g in sorted(groups, key=lambda g: (bool(g.get('isDefault')), g['weight']))]
                if headings != expected_titles:
                    document['gaps'].append('china_section_ui_mismatch')

            document['completion']['china_boards_checked'] = len(china)
        except Exception:
            document['gaps'].append('ui_inventory_verification_incomplete')

    if not document['gaps']:
        document['status'] = 'complete'
    document['gaps'] = sorted(set(document['gaps']))
    page.close()
    return document, transport


def open_browser(playwright, profile):
    return playwright.chromium.launch_persistent_context(str(profile), channel='chrome', headless=True,
        ignore_default_args=['--use-mock-keychain', '--password-store=basic'])


def fresh_context(persistent):
    # Cookies stay in memory. A clean context forces a full UI sync rather than
    # reading IndexedDB/private app internals or mistaking deltas for inventory.
    return persistent.browser.new_context(storage_state={'cookies': persistent.cookies(), 'origins': []},
                                          service_workers='block', viewport={'width': 1440, 'height': 1000})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    with sync_playwright() as p:
        persistent = open_browser(p, args.profile)
        context = fresh_context(persistent)
        document, _ = collect_yaay(context)
        args.output.write_text(json.dumps(document, ensure_ascii=False))
        print(json.dumps({'source': 'yaay', 'status': document['status'], 'items': len(document['items']),
                          'collections': len(document['collections']), 'memberships': len(document['memberships']),
                          'gaps': document['gaps'], 'completion': document['completion']}))
        context.close()
        persistent.close()


if __name__ == '__main__':
    main()
