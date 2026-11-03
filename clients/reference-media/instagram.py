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


def advance(context, cookies, saved_url, path, page_budget=8):
    if path.exists():
        state = json.loads(path.read_text())
    else:
        collections = roots(context, saved_url)
        state = {'document': empty_document('instagram'), 'roots': collections,
                 'cursor': {}, 'done': [], 'started': time.time(), 'pages': 0}
        state['document']['collections'] = [{k: c[k] for k in ('id', 'title', 'ordinal', 'parent')} for c in collections]
        atomic_json(path, state)
    document = state['document']
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
        filed = {m['item_id'] for m in membership.values() if m['collection_id'] != 'all'}
        document['collections'].append({'id': 'unfiled', 'parent': None, 'title': 'Unfiled', 'ordinal': -1})
        for m in list(membership.values()):
            if m['collection_id'] == 'all' and m['item_id'] not in filed:
                membership[('unfiled', m['item_id'])] = dict(m, collection_id='unfiled')
        document['status'] = 'complete'
    document['completion'] = {'authenticated': True, 'roots_complete': True,
                              'pagination_complete': document['status'] == 'complete',
                              'visited_collections': len(document['collections']), 'pages': state['pages'],
                              'method': 'visible-root-grid-and-gallery-dl-explicit-pagination'}
    # Each submitted progress snapshot is immutable; the checkpoint retains its
    # separate scan identity while submissions get independent retry identities.
    save()
    return document
