"""Read rendered Yaay board order; transport URLs stay in memory only."""
from collections import Counter, defaultdict
import json
import time
from urllib.parse import parse_qs, urlsplit


def image_key(url):
    if not url:
        return None
    if '/https://' in url:
        url = 'https://' + url.split('/https://', 1)[1]
    parsed = urlsplit(url)
    return parsed.hostname, parsed.path


CARD = 'div.flex.flex-col.relative.w-full.h-full'
ROWS = '''body => [...body.querySelectorAll('h3,div.flex.flex-col.relative.w-full.h-full')].map(e=>({
 tag:e.tagName, title:e.tagName==='H3'?e.textContent:e.querySelector('p')?.textContent,
 image:e.tagName==='H3'?null:e.querySelector('img')?.src
}))'''


def inspect_saved(context, capture, document, output):
    item_keys = {item['id']: item['source_key'] for item in document['items']}
    thumbnails = defaultdict(set)
    for identity, node in capture.nodes['saved'].items():
        key = image_key(node['item'].get('thumbnailUrl'))
        if key and identity in item_keys:
            thumbnails[key].add(item_keys[identity])
    expected = list(dict.fromkeys(item_keys[m['item_id']] for m in sorted(document['memberships'], key=lambda m: m['ordinal'])
                                 if m['collection_id'] == 'all'))
    result = {'started': time.time(), 'source_keys': [], 'unknown_cards': [], 'stable_end': False}
    seen, unknown, previous, stable = set(), set(), None, 0
    page = context.new_page()
    try:
        page.goto('https://yaaytravel.com/saved/?showBottomDrawer=expanded', wait_until='domcontentloaded')
        page.locator(CARD).first.wait_for(state='attached', timeout=30000)
        for attempt in range(200):
            rows = page.locator(CARD).evaluate_all('els=>els.map(e=>({image:e.querySelector("img")?.src,title:e.querySelector("p")?.textContent}))')
            for row in rows:
                candidates = thumbnails.get(image_key(row.get('image')), set())
                if len(candidates) == 1:
                    key = next(iter(candidates))
                    if key not in seen:
                        result['source_keys'].append(key)
                        seen.add(key)
                else:
                    # No URL is exported, including for unidentifiable images.
                    marker = (row.get('title'), image_key(row.get('image')))
                    if marker not in unknown:
                        result['unknown_cards'].append({'title': row.get('title'), 'after_known_posts': len(seen),
                                                        'candidate_keys': sorted(candidates)})
                        unknown.add(marker)
            current = (tuple(result['source_keys']), len(unknown))
            stable = stable + 1 if current == previous else 0
            if stable >= 8:
                result['stable_end'] = True
                break
            previous = current
            page.locator(CARD).last.scroll_into_view_if_needed()
            page.keyboard.press('End')
            page.wait_for_timeout(500)
            if attempt % 10 == 0:
                print(json.dumps({'yaay_saved_known_posts': len(seen), 'unknown_cards': len(unknown)}), flush=True)
        result['expected_unique_posts'] = len(expected)
        result['missing_keys'] = sorted(set(expected) - seen)
        result['extra_keys'] = sorted(seen - set(expected))
        result['known_order_equals_inventory'] = result['source_keys'] == [key for key in expected if key in seen]
        result['finished'] = time.time()
        output.write_text(json.dumps(result, ensure_ascii=False))
    finally:
        page.close()
    return result


def inspect_boards(context, capture, document, output, resume=False):
    thumbs, titles = defaultdict(list), defaultdict(list)
    for identity, node in capture.nodes['saved'].items():
        if node.get('deleted'):
            continue
        key = image_key(node['item'].get('thumbnailUrl'))
        if key:
            thumbs[key].append(identity)
    for item in document['items']:
        titles[item['metadata'].get('title')].append(item['id'])
    page = context.new_page()
    result = json.loads(output.read_text()) if resume else {'started': time.time(), 'boards': [], 'root_ids': [], 'errors': []}
    if resume:
        result['resumed_at'] = time.time()
        result['boards'] = [b for b in result['boards'] if 'TimeoutError' not in b['gaps']]

    def save():
        temporary = output.with_suffix('.new')
        temporary.write_text(json.dumps(result, ensure_ascii=False))
        temporary.replace(output)

    try:
        page.goto('https://yaaytravel.com/boards/?showBottomDrawer=expanded', wait_until='domcontentloaded')
        page.locator('a[href*="/boards/view/"]').first.wait_for(state='attached', timeout=30000)
        links = page.locator('a[href*="/boards/view/"]').evaluate_all('(els)=>els.map(e=>e.getAttribute("href"))')
        root_ids = [parse_qs(urlsplit(link).query)['boardId'][0] for link in links]
        if resume and result['root_ids'] != root_ids:
            raise ValueError('roots_changed_during_ui_audit')
        result['root_ids'] = root_ids
        expected_roots = [c['id'][2:] for c in document['collections'] if c['id'].startswith('b:')]
        result['root_identity_parity'] = Counter(result['root_ids']) == Counter(expected_roots)
        result['root_order_equals_inventory'] = result['root_ids'] == expected_roots
        for link, bid in zip(links, result['root_ids'], strict=True):
            if any(b['id'] == 'b:' + bid for b in result['boards']):
                continue
            board = {'id': 'b:' + bid, 'sections': [], 'gaps': []}
            expected_sections = [c for c in document['collections'] if c.get('parent') == board['id']]
            expected_ids = {c['id'] for c in expected_sections}
            expected_count = sum(m['collection_id'] in expected_ids for m in document['memberships'])
            try:
                page.goto('https://yaaytravel.com' + link, wait_until='domcontentloaded')
                title = next(c['title'] for c in document['collections'] if c['id'] == board['id'])
                page.get_by_role('heading', name=title, level=2, exact=True).wait_for(state='attached', timeout=30000)
                previous, stable = None, 0
                for _ in range(15):
                    raw = page.locator('body').evaluate(ROWS)
                    implicit = len(expected_sections) == 1 and not any(row['tag'] == 'H3' for row in raw)
                    sections = [{'title': expected_sections[0]['title'], 'cards': []}] if implicit else []
                    for row in raw:
                        if row['tag'] == 'H3':
                            sections.append({'title': row['title'], 'cards': []})
                        elif sections:
                            candidates = thumbs.get(image_key(row.get('image')), [])
                            method = 'thumbnail_identity'
                            if not candidates:
                                candidates = titles.get(row.get('title'), [])
                                method = 'title_only'
                            sections[-1]['cards'].append({'ids': candidates, 'method': method, 'title': row.get('title')})
                    current = json.dumps(sections, sort_keys=True)
                    stable = stable + 1 if current == previous else 0
                    if stable >= 3:
                        break
                    previous = current
                    page.locator('body').press('End')
                    page.wait_for_timeout(300)
                else:
                    board['gaps'].append('unstable_ui')
                board['expected_memberships'] = expected_count
                board['implicit_single_section'] = implicit
                board['visible_cards'] = sum(len(s['cards']) for s in sections)
                if board['visible_cards'] != expected_count:
                    board['gaps'].append('visible_membership_count')
                unused = {c['id']: c for c in expected_sections}
                for section in sections:
                    candidates = [c for c in unused.values() if c['title'] == section['title']]
                    observed_ids = [card['ids'][0] for card in section['cards'] if len(card['ids']) == 1]
                    if len(candidates) > 1:
                        candidates = [c for c in candidates if Counter(observed_ids) == Counter(
                            m['item_id'] for m in document['memberships'] if m['collection_id'] == c['id'])]
                    if len(candidates) == 1:
                        cid = candidates[0]['id']
                        section['id'] = cid
                        unused.pop(cid)
                        expected = [m['item_id'] for m in sorted(document['memberships'], key=lambda m: m['ordinal'])
                                    if m['collection_id'] == cid]
                        section['identities_equal'] = Counter(observed_ids) == Counter(expected)
                        section['order_equals_inventory'] = observed_ids == expected
                    else:
                        board['gaps'].append('ambiguous_section_identity')
                    if any(len(card['ids']) != 1 or card['method'] != 'thumbnail_identity' for card in section['cards']):
                        board['gaps'].append('card_identity_needs_confirmation')
                if unused:
                    board['gaps'].append('sections_missing_in_ui')
                board['sections'] = sections
                board['section_order'] = [s.get('id') for s in sections]
            except Exception as error:
                board['gaps'].append(type(error).__name__)
            board['checked_at'] = time.time()
            result['boards'].append(board)
            save()
            print(json.dumps({'yaay_boards_checked': len(result['boards']), 'total': len(links)}), flush=True)
    finally:
        page.close()
    result['finished'] = time.time()
    result['boards'].sort(key=lambda b: result['root_ids'].index(b['id'][2:]))
    save()
    return result
