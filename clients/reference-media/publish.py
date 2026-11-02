"""Publish importer-owned metadata only; never rewrite project boards or notes."""
import hashlib
import json
from datetime import datetime, timezone
from instagram import atomic_json

START, END = '<!-- reference-import:start -->', '<!-- reference-import:end -->'


def slug(identity):
    return hashlib.sha256(identity.encode()).hexdigest()[:24]


def managed(path, body):
    block = START + '\n' + body + '\n' + END
    if path.exists():
        previous = path.read_text()
        if previous.count(START) != 1 or previous.count(END) != 1:
            raise ValueError('importer_note_markers_changed')
        updated = previous[:previous.index(START)] + block + previous[previous.index(END) + len(END):]
    else:
        updated = '---\nprivate: true\n---\n\n' + block + '\n\nYour annotations:\n'
    if not path.exists() or path.read_text() != updated:
        temporary = path.with_suffix('.md.new')
        temporary.write_text(updated)
        temporary.replace(path)


def publish(vault, catalog, state):
    root = vault / 'References'
    for folder in ('Sources', 'Collections', 'Thumbnails'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    for asset in catalog['assets']:
        thumbnail = root / 'Thumbnails' / (asset['id'] + '.jpg')
        if thumbnail.exists():
            asset['thumbnail'] = 'References/Thumbnails/' + thumbnail.name
    atomic_json(root / 'Catalog.json', catalog)
    assets_by_key = {}
    for asset in catalog['assets']:
        for origin in asset['origins']:
            assets_by_key.setdefault(origin['source_key'], {})[asset['id']] = (asset, origin['ordinal'])
    by_source = {(i['source'], i['id']): i for i in catalog.get('items', [])}
    by_key = {}
    for item in by_source.values():
        by_key.setdefault(item['source_key'], []).append(item)
    for key, origins in by_key.items():
        title = next((i['metadata'].get('title') for i in origins if i['metadata'].get('title')), key)
        body = '# ' + title.replace('\n', ' ') + '\n\n'
        for item in origins:
            metadata = item['metadata']
            url = item.get('url')
            body += f"{item['source'].title()}" + (f" · [Source](<{url}>)" if url else '') + '\n\n'
            if metadata.get('attribution'):
                body += 'Attribution: ' + metadata['attribution'] + '\n\n'
            body += (metadata.get('caption') or metadata.get('description') or metadata.get('note') or '') + '\n\n'
            for place in metadata.get('places', []):
                label = place.get('title') or 'Unresolved place'
                link = place.get('map_url')
                if not link and place.get('latitude') is not None and place.get('longitude') is not None:
                    link = 'https://www.openstreetmap.org/?mlat=' + str(place['latitude']) + '&mlon=' + str(place['longitude'])
                body += '- ' + (f'[{label}](<{link}>)' if link else label) + ' · provenance: ' + place.get('provenance', 'unknown')
                if place.get('segmentTimestamp') is not None:
                    body += ' · source timestamp: ' + str(place['segmentTimestamp'])
                body += '\n'
        if key in state.get('retry', {}):
            body += '\nAcquisition needs retry; original source may be unavailable. Previous media are retained.\n'
        assets = sorted(assets_by_key.get(key, {}).values(), key=lambda pair: pair[1])
        body += '\nArchived members: ' + str(len(assets)) + '\n\n'
        for asset, ordinal in assets:
            thumbnail = root / 'Thumbnails' / (asset['id'] + '.jpg')
            if thumbnail.exists():
                body += '![[References/Thumbnails/' + thumbnail.name + '|240]]\n\n'
            body += f"- Member {ordinal + 1}: `{asset['id']}`\n"
        if not assets:
            body += '\nAwaiting acquisition. A missing or unavailable source is retained here.\n'
        managed(root / 'Sources' / (slug(key) + '.md'), body)
    collections = {(c['source'], c['id']): c for c in catalog['collections']}
    for key, collection in collections.items():
        cid = slug(':'.join(key))
        body = '# ' + (collection['title'] or '(unnamed list)') + '\n\n'
        body += ('Current source list' if collection['active'] else 'Retained list — absent from latest complete scan') + '\n\n'
        if collection['parent']:
            parent = collections.get((collection['source'], collection['parent']))
            if parent:
                body += f"Parent: [[References/Collections/{slug(parent['source'] + ':' + parent['id'])}|{parent['title']}]]\n\n"
        for child in collections.values():
            if child['source'] == collection['source'] and child['parent'] == collection['id']:
                body += f"- [[References/Collections/{slug(child['source'] + ':' + child['id'])}|{child['title'] or '(unnamed list)'}]]\n"
        for member in catalog.get('memberships', []):
            if (member['source'], member['collection_id']) != key:
                continue
            item = by_source[(member['source'], member['item_id'])]
            title = (item['metadata'].get('title') or item['id']).replace('|', ' ').replace(']', '').replace('\n', ' ')
            body += f"- [[References/Sources/{slug(item['source_key'])}|{title}]]" + ('' if member['active'] else ' (retained after removal)') + '\n'
            note = json.loads(member['metadata']).get('note')
            if note:
                body += '  ' + note.replace('\n', '\n  ') + '\n'
        managed(root / 'Collections' / (cid + '.md'), body)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    body = '# Reference archive\n\nUpdated: ' + now + '\n\n'
    body += f"Archived assets: {catalog['counts']['assets']} · completed posts: {catalog['counts']['completed_posts']}\n\n"
    for source in catalog['sources']:
        body += f"- {source['source'].title()} inventory: **{source['status']}**\n"
    body += '\nWorker: ' + state.get('phase', 'idle') + '\n\n'
    body += f"Pending posts: {state.get('pending_posts', 'checking')} · delayed retries: {len(state.get('retry', {}))}\n\n"
    for issue in state.get('issues', []):
        body += '- ' + issue + '\n'
    body += '\nOpen an Excalidraw drawing, then use **Reference Boards: Add a reference to this board**. Choose a downloaded asset by title or collection. Use **Choose excerpt or capture frame on this board** to change one card.\n\nCollections:\n\n'
    for c in catalog['collections']:
        if c['parent'] is None:
            body += f"- [[References/Collections/{slug(c['source'] + ':' + c['id'])}|{c['source'].title()} / {c['title']}]]\n"
    managed(root / 'Archive.md', body)
