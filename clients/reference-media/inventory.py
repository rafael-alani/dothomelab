"""Source identity and lossless hierarchy normalization, independent of downloads."""
import re
import uuid
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def public_url(value):
    if not value:
        return None
    url = urlsplit(value)
    if url.scheme not in {'http', 'https'} or url.username or url.password:
        return None
    # Tracking and signed CDN query strings are never catalogue identity.
    query = urlencode([(k, v) for k, v in parse_qsl(url.query)
                       if k in {'q', 'query', 'll', 'destination', 'destination_place_id', 'mlat', 'mlon', 'v', 'api', 'query_place_id', 'cid'}])
    return urlunsplit(('https', url.netloc, url.path, query, ''))


def identity(url, fallback):
    parsed = urlsplit(url or '')
    if (parsed.hostname or '').removeprefix('www.') == 'instagram.com':
        match = re.match(r'/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)', parsed.path)
        if match:
            return 'instagram:' + match[1], 'https://www.instagram.com/p/' + match[1] + '/'
    return 'yaay:' + fallback, public_url(url)


def empty_document(source):
    return {'source': source, 'scan_id': str(uuid.uuid4()), 'status': 'partial',
            'collections': [], 'items': [], 'memberships': [], 'gaps': []}


def yaay_document(boards, saved):
    document, transport = empty_document('yaay'), {}
    items = {}
    for saved_id, node in saved.items():
        if node.get('deleted'):
            continue
        item = node['item']
        external = node.get('externalInfo') or {}
        key, url = identity(item.get('externalUrl'), saved_id)
        places = []
        for match in node.get('matches', []):
            place = {field: match.get(field) for field in (
                'id', 'matchId', 'title', 'description', 'country', 'city', 'address',
                'latitude', 'longitude', 'segmentTimestamp', 'sourceType', 'sourcePlatform')}
            place.update(provenance='yaay', resolved=match.get('latitude') is not None,
                         source_url=public_url(match.get('sourceUrl')), map_url=public_url(match.get('googleMapsLink')))
            places.append(place)
        metadata = {'title': item.get('title') or external.get('originalTitle') or (item.get('description') or 'Saved reference')[:100],
                    'description': item.get('description'), 'caption': external.get('originalDescription'),
                    'attribution': external.get('authorNickname') or external.get('authorName'),
                    'source_created': item.get('createdAt'), 'places': places,
                    'availability': item.get('state'), 'carousel_members': []}
        # These are ephemeral transport URLs in memory only, never scan output.
        media = []
        members = [item] + node.get('additionalContent', [])
        for ordinal, member in enumerate(members):
            metadata['carousel_members'].append({'id': member['id'], 'ordinal': ordinal,
                                                'kind': member.get('contentType', member.get('savedType'))})
            remote = member.get('videoUrl') or member.get('thumbnailUrl')
            if remote:
                media.append({'url': remote, 'ordinal': ordinal, 'kind': 'video' if member.get('videoUrl') else 'image'})
        transport[key] = media
        items[saved_id] = {'id': saved_id, 'source_key': key, 'url': url, 'metadata': metadata}
    document['collections'].append({'id': 'all', 'parent': None, 'title': 'All saved', 'ordinal': -2})
    document['collections'].append({'id': 'unfiled', 'parent': None, 'title': 'Unfiled', 'ordinal': -1})
    filed = set()
    visited = set()

    def group_tree(group, parent):
        if group.get('deletedAt'):
            return
        group_id = 'g:' + group['id']
        if group_id in visited:
            raise ValueError('repeated_or_cyclic_group')
        visited.add(group_id)
        document['collections'].append({'id': group_id, 'parent': parent,
                                        'title': group.get('title') or '', 'ordinal': group['weight']})
        for member in group.get('items', []):
            if member.get('deletedAt'):
                continue
            saved_id = member.get('savedId')
            if saved_id is None:
                # Retain non-media board notes/URLs; they have independent IDs.
                saved_id = 'board-item-' + member['id']
                items[saved_id] = {'id': saved_id, 'source_key': 'yaay:' + member['id'],
                                   'url': public_url(member.get('url')),
                                   'metadata': {'title': 'Board note', 'note': member.get('note'),
                                                'attachment_url': public_url(member.get('attachmentUrl'))}}
            elif saved_id not in items:
                document['gaps'].append('board_references_unavailable_saved_item')
                items[saved_id] = {'id': saved_id, 'source_key': 'yaay:' + saved_id, 'url': None,
                                   'metadata': {'title': 'Unavailable saved item', 'availability': 'unavailable'}}
            filed.add(saved_id)
            document['memberships'].append({'collection_id': group_id, 'item_id': saved_id,
                                            'ordinal': member['weight'], 'source_membership_id': member['id'],
                                            'note': member.get('note')})
        # Recurse without a depth cap; fixtures cover deeper and reparented trees.
        # Current observed Yaay schema has groups at board level only.
        for child in group.get('groups', []):
            group_tree(child, group_id)

    active_boards = [b for b in boards.values() if not b.get('deleted') and not b['item'].get('deletedAt')]
    for board in sorted(active_boards, key=lambda b: b['item']['weight']):
        item = board['item']
        board_id = 'b:' + item['id']
        document['collections'].append({'id': board_id, 'parent': None, 'title': item['title'], 'ordinal': item['weight']})
        before = len(document['memberships'])
        for group in board.get('groups', []):
            group_tree(group, board_id)
        if len(document['memberships']) - before != board['itemCount']:
            document['gaps'].append('board_item_count_mismatch')
    for ordinal, saved_id in enumerate(sorted(saved, key=lambda identity: (saved[identity]['item'].get('createdAt') or '', identity), reverse=True)):
        if saved_id not in items:
            continue
        document['memberships'].append({'collection_id': 'all', 'item_id': saved_id, 'ordinal': ordinal})
        if saved_id not in filed:
            document['memberships'].append({'collection_id': 'unfiled', 'item_id': saved_id, 'ordinal': ordinal})
    document['items'] = list(items.values())
    document['gaps'] = sorted(set(document['gaps']))
    return document, transport
