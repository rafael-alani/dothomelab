"""Independent, resumable collection inventory using gallery-dl's maintained API."""
import json
import re
import time
from urllib.parse import urlsplit
from gallery_dl import extractor, config
from downloader import configure
from inventory import empty_document


class PageBudget(Exception):
    pass


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.new')
    temporary.write_text(json.dumps(value, ensure_ascii=False))
    temporary.replace(path)


def roots(context, saved_url):
    page = context.new_page()
    try:
        page.goto(saved_url, wait_until='domcontentloaded', timeout=60000)
        page.locator('a[href*="/saved/all-posts/"]').wait_for(timeout=45000)
        # Collection cards are a finite grid. Scroll its visible UI to the end;
        # require a stable final set before recording root coverage.
        previous, stable, observed = None, 0, {}
        for _ in range(30):
            links = page.locator('a[href*="/saved/"]').evaluate_all('(els)=>els.map(e=>({url:e.href,title:e.innerText}))')
            for link in links:
                if link['title']:
                    observed[link['url']] = link
            current = sorted(observed)
            stable = stable + 1 if current == previous else 0
            if stable == 3:
                break
            previous = current
            page.locator('a[href*="/saved/"]').last.scroll_into_view_if_needed()
            page.mouse.wheel(0, 600)
            page.wait_for_timeout(1000)
        else:
            raise ValueError('instagram_root_pagination_incomplete')
        result = []
        for link in observed.values():
            path = urlsplit(link['url']).path
            if path.endswith('/saved/all-posts/'):
                identity = 'all'
            elif match := re.search(r'/saved/[^/]+/(\d+)/?$', path):
                identity = match[1]
            else:
                continue  # Audio is a soundtrack picker, separate from saved posts.
            result.append({'id': identity, 'title': link['title'], 'url': link['url'],
                           'ordinal': len(result), 'parent': None})
        if not any(c['id'] == 'all' for c in result):
            raise ValueError('instagram_needs_sign_in')
        return result
    finally:
        page.close()


def normalize(post):
    code = post['code']
    if not re.fullmatch('[A-Za-z0-9_-]+', code):
        raise ValueError('invalid_instagram_identity')
    caption = (post.get('caption') or {}).get('text') or ''
    location = post.get('location') or {}
    places = []
    if location:
        places.append({'provenance': 'instagram_location_tag', 'title': location.get('name'),
                       'latitude': location.get('lat'), 'longitude': location.get('lng'),
                       'resolved': location.get('lat') is not None, 'id': str(location.get('pk', ''))})
    members = post.get('carousel_media') or [post]
    return {'id': str(post['pk']), 'source_key': 'instagram:' + code,
            'url': 'https://www.instagram.com/p/' + code + '/',
            'metadata': {'title': caption.split('\n')[0][:100] or code, 'caption': caption,
                         'attribution': (post.get('user') or {}).get('username'),
                         'source_created': post.get('taken_at'), 'places': places,
                         'carousel_members': [{'id': str(m['pk']), 'ordinal': i, 'kind': 'video' if m.get('media_type') == 2 else 'image'} for i, m in enumerate(members)]}}


def shortcode_id(code):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,16}', code):
        raise ValueError('invalid_instagram_identity')
    value = 0
    for char in code:
        value = value * 64 + alphabet.index(char)
    return str(value)


def collection_grid(context, url):
    """Accumulate the virtualized grid, including posts absent from the v1 API."""
    page = context.new_page()
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        page.locator('main h3').wait_for(timeout=45000)
        if urlsplit(page.url).path.rstrip('/').split('/')[-1] != urlsplit(url).path.rstrip('/').split('/')[-1]:
            raise ValueError('instagram_collection_redirected')
        observed, previous, stable = {}, None, 0
        selector = 'main a[href*="/reel/"], main a[href*="/p/"]'
        for _ in range(400):
            rows = page.locator(selector).evaluate_all("""els => els.map(e => ({
                url: e.getAttribute('href'), caption: e.querySelector('img')?.alt || '',
                thumbnail: e.querySelector('img')?.src,
                kind: e.querySelector('[aria-label="Carousel"]') ? 'carousel' :
                      e.getAttribute('href').includes('/reel/') || e.querySelector('[aria-label="Clip"]') ? 'video' : 'image'
            }))""")
            for row in rows:
                match = re.fullmatch(r'/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/([A-Za-z0-9_-]+)/?', row['url'])
                if match:
                    observed.setdefault(match[1], row)
            current = list(observed)
            loading = page.get_by_role('progressbar').count()
            stable = stable + 1 if current == previous and not loading else 0
            if stable >= 3:
                # An empty DOM is also a transient/error/login response, never
                # evidence that a collection was cleared.
                if not observed:
                    raise ValueError('instagram_empty_grid_unverified')
                return [dict(row, code=code) for code, row in observed.items()]
            previous = current
            page.locator('body').press('End')
            page.wait_for_timeout(1200)
        raise ValueError('instagram_grid_pagination_incomplete')
    finally:
        page.close()


def reconcile_grid(document, cid, rows):
    """UI order is collection order; never synthesize dates or archived media."""
    items = {i['source_key']: i for i in document['items']}
    api = [m for m in document['memberships'] if m['collection_id'] == cid]
    by_id = {i['id']: i for i in document['items']}
    api_keys = [by_id[m['item_id']]['source_key'] for m in sorted(api, key=lambda m: m['ordinal'])]
    keys = ['instagram:' + row['code'] for row in rows]
    if len(set(keys)) != len(keys) or not keys:
        raise ValueError('instagram_invalid_grid')
    missing, extra = sorted(set(keys) - set(api_keys)), sorted(set(api_keys) - set(keys))
    # Disagreement can indicate a concurrent save or a UI failure. Preserve both
    # observations and prohibit retirement until a subsequent scan agrees.
    document['memberships'] = [m for m in document['memberships'] if m['collection_id'] != cid]
    for ordinal, row in enumerate(rows):
        key = 'instagram:' + row['code']
        item = items.get(key)
        if item is None:
            item = {'id': shortcode_id(row['code']), 'source_key': key,
                    'url': 'https://www.instagram.com/p/' + row['code'] + '/',
                    'metadata': {'title': row['caption'].split('\n')[0][:100] or row['code'],
                                 'caption': row['caption'], 'attribution': row['url'].split('/')[1],
                                 'source_created': None, 'inventory_provenance': 'visible_collection_grid',
                                 'media_kind': row['kind'], 'carousel_members': []}}
            items[key] = item
        document['memberships'].append({'collection_id': cid, 'item_id': item['id'], 'ordinal': ordinal})
    for m in api:
        if by_id[m['item_id']]['source_key'] in extra:
            document['memberships'].append(dict(m, ordinal=len(rows) + m['ordinal']))
    document['items'] = list(items.values())
    return {'ui_posts': len(rows), 'api_posts': len(api_keys), 'ui_only': missing,
            'api_only': extra, 'order': 'source_collection_grid', 'checked_at': time.time()}


def advance(context, cookies, saved_url, path, page_budget=8, thumbnail_dir=None):
    if path.exists():
        state = json.loads(path.read_text())
    else:
        collections = roots(context, saved_url)
        state = {'document': empty_document('instagram'), 'roots': collections,
                 'cursor': {}, 'done': [], 'started': time.time(), 'pages': 0}
        state['document']['collections'] = [{k: c[k] for k in ('id', 'title', 'ordinal', 'parent')} for c in collections]
        atomic_json(path, state)
    document = state['document']
    # Older checkpoints certified only root coverage, not individual grids.
    for cid in list(state['done']):
        if cid not in state.get('collection_audits', {}):
            state['done'].remove(cid)
            state['cursor'].pop(cid, None)
            document['memberships'] = [m for m in document['memberships'] if m['collection_id'] != cid]
    restarting = state.pop('restart_collections', [])
    document['memberships'] = [m for m in document['memberships'] if m['collection_id'] not in restarting]
    by_id = {item['id']: item for item in document['items']}
    membership = {(m['collection_id'], m['item_id']): m for m in document['memberships']}
    used = 0
    def save():
        document['items'] = list(by_id.values())
        document['memberships'] = list(membership.values())
        atomic_json(path, state)
    for collection in state['roots']:
        cid = collection['id']
        if cid in state['done']:
            continue
        configure(cookies)
        config.set(('extractor', 'instagram'), 'cursor', state['cursor'].get(cid) or True)
        ext = extractor.find(collection['url'])
        if ext is None:
            raise ValueError('unsupported_instagram_collection')
        ext.initialize()
        ext.login()
        if not ext._logged_in:
            raise ValueError('instagram_needs_sign_in')
        original = ext.api._call
        def checked_call(endpoint, **kwargs):
            nonlocal used
            if page_budget is not None and used >= page_budget:
                raise PageBudget()
            result = original(endpoint, **kwargs)
            if result.get('status') != 'ok' or not isinstance(result.get('more_available'), bool) or not isinstance(result.get('items'), list):
                raise ValueError('instagram_page_not_complete')
            if result['more_available'] and not result.get('next_max_id'):
                raise ValueError('instagram_cursor_missing')
            used += 1
            state['pages'] += 1
            return result
        ext.api._call = checked_call
        original_cursor = ext._update_cursor
        def checkpoint(cursor):
            state['cursor'][cid] = cursor
            save()  # Advance only after every item on that page was normalized.
            return original_cursor(cursor)
        ext._update_cursor = checkpoint
        ordinal = sum(m['collection_id'] == cid for m in membership.values())
        try:
            for post in ext.posts():
                item = normalize(post)
                by_id[item['id']] = item
                key = (cid, item['id'])
                if key not in membership:
                    membership[key] = {'collection_id': cid, 'item_id': item['id'], 'ordinal': ordinal}
                    ordinal += 1
            save()
            rows = collection_grid(context, collection['url'])
            audit = reconcile_grid(document, cid, rows)
            state.setdefault('collection_audits', {})[cid] = audit
            by_id = {item['id']: item for item in document['items']}
            membership = {(m['collection_id'], m['item_id']): m for m in document['memberships']}
            if thumbnail_dir is not None:
                from hashlib import sha256
                for row in rows:
                    url = row.get('thumbnail') or ''
                    parsed = urlsplit(url)
                    target = thumbnail_dir / ('post-' + sha256(('instagram:' + row['code']).encode()).hexdigest()[:24] + '.jpg')
                    if target.exists() or parsed.scheme != 'https' or not any((parsed.hostname or '').endswith('.' + host) for host in ('cdninstagram.com', 'fbcdn.net')):
                        continue
                    try:
                        response = context.request.get(url, timeout=15000)
                        try:
                            data = response.body()
                            if response.ok and response.headers.get('content-type', '').startswith('image/jpeg') and len(data) <= 1024 * 1024:
                                target.parent.mkdir(parents=True, exist_ok=True)
                                target.write_bytes(data)
                        finally:
                            response.dispose()
                    except Exception:
                        pass  # Inventory is independent of optional thumbnails.
            state['done'].append(cid)
            save()
        except PageBudget:
            save()
            break
        finally:
            ext.session.close()
    if len(state['done']) == len(state['roots']):
        current = roots(context, saved_url)
        if [(c['id'], c['title']) for c in current] != [(c['id'], c['title']) for c in state['roots']]:
            atomic_json(path.with_name('instagram-scan.previous.json'), state)
            path.unlink()
            raise ValueError('instagram_roots_changed_restart')
        # Derived memberships must be rebuilt after a disagreement retry: a post
        # that was unfiled in the first observation may now belong to a collection.
        membership = {key: m for key, m in membership.items() if m['collection_id'] != 'unfiled'}
        filed = {m['item_id'] for m in membership.values() if m['collection_id'] != 'all'}
        document['collections'] = [c for c in document['collections'] if c['id'] != 'unfiled']
        document['collections'].append({'id': 'unfiled', 'parent': None, 'title': 'Unfiled', 'ordinal': -1})
        for m in list(membership.values()):
            if m['collection_id'] == 'all' and m['item_id'] not in filed:
                membership[('unfiled', m['item_id'])] = dict(m, collection_id='unfiled')
        if any(audit['api_only'] for audit in state.get('collection_audits', {}).values()):
            document['gaps'] = ['instagram_api_ui_disagreement_retry']
            for cid, audit in state['collection_audits'].items():
                if audit['api_only']:
                    state['done'].remove(cid)
                    state['cursor'].pop(cid, None)
                    # Return this partial union once; next attempt starts this
                    # collection afresh, without dropping server history.
                    state.setdefault('restart_collections', []).append(cid)
        else:
            document['gaps'] = [gap for gap in document['gaps'] if gap != 'instagram_api_ui_disagreement_retry']
            document['status'] = 'complete'
    document['completion'] = {'authenticated': True, 'roots_complete': True,
                              'pagination_complete': document['status'] == 'complete',
                              'visited_collections': len(document['collections']), 'pages': state['pages'],
                              'method': 'visible-root-and-collection-grids-with-gallery-dl-pagination',
                              'collection_audits': state.get('collection_audits', {})}
    # Each submitted progress snapshot is immutable; the checkpoint retains its
    # separate scan identity while submissions get independent retry identities.
    save()
    return document
