#!/usr/bin/env python3
"""Compare fresh source observations with a read-only server audit ledger."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


def membership_id(member):
    return member.get('source_membership_id') or member['collection_id'] + ':' + member['item_id']


def compare(ledger, observed, media_kinds=None):
    source = observed['source']
    items = {i['id']: i for i in observed['items']}
    stored = {i['id']: i for i in ledger['source_items'] if i['source'] == source}
    members = {membership_id(m): m for m in observed['memberships']}
    active = {m['identity']: m for m in ledger['membership_entries'] if m['source'] == source and m['active']}
    historical = {m['identity']: m for m in ledger['membership_entries'] if m['source'] == source and not m['active']}
    collections = {c['id']: c for c in observed['collections']}
    old_collections = {c['id']: c for c in ledger['collections'] if c['source'] == source and c['active']}
    receipts = {r['source_key']: r for r in ledger['completed_posts']}
    assets = {a['id']: a for a in ledger['assets']}
    result = {'source': source, 'source_status': observed['status'], 'source_gaps': observed['gaps'],
              'new_items': sorted(set(items) - set(stored)),
              'stored_items_absent_from_source': sorted(set(stored) - set(items)),
              'new_collections': sorted(set(collections) - set(old_collections)),
              'removed_collections': sorted(set(old_collections) - set(collections)),
              'changed_collections': [], 'identity_changes': [], 'media_metadata_changes': [],
              'missing_current_memberships': sorted(set(members) - set(active)),
              'stale_current_memberships': sorted(set(active) - set(members)),
              'reactivated_memberships': sorted(set(historical) & set(members)),
              'historical_absent_memberships': sorted(set(historical) - set(members)),
              'changed_memberships': [], 'receipt_discrepancies': [], 'collections': []}
    for identity in set(collections) & set(old_collections):
        if any(collections[identity].get(k) != old_collections[identity].get(k) for k in ('title', 'parent', 'ordinal')):
            result['changed_collections'].append(identity)
    for identity in set(members) & set(active):
        changed = {k: {'source': members[identity][k], 'server': active[identity][k]}
                   for k in ('collection_id', 'item_id', 'ordinal') if members[identity][k] != active[identity][k]}
        if changed:
            result['changed_memberships'].append({'identity': identity, 'changes': changed})
    for identity, item in items.items():
        expected = item.get('metadata', {}).get('carousel_members', [])
        if identity in stored:
            if item['source_key'] != stored[identity]['source_key']:
                result['identity_changes'].append(identity)
            if expected != stored[identity]['members']:
                result['media_metadata_changes'].append({'id': identity, 'source_key': item['source_key'],
                                                         'source': expected, 'server': stored[identity]['members']})
        receipt = receipts.get(item['source_key'])
        if not receipt:
            result['receipt_discrepancies'].append({'source_key': item['source_key'], 'error': 'missing_receipt'})
            continue
        received = sorted(receipt['members'], key=lambda m: m['ordinal'])
        errors = []
        if len(received) != len(expected):
            errors.append('member_count')
        if [m['ordinal'] for m in received] != list(range(len(received))):
            errors.append('noncontiguous_or_duplicate_ordinals')
        kinds = ['video' if Path(assets[m['id']]['path']).suffix in {'.mp4', '.mov', '.webm'} else 'image'
                 for m in received]
        transport_kinds = {m['ordinal']: m['kind'] for m in (media_kinds or {}).get(item['source_key'], [])}
        for index, member in enumerate(expected):
            # Yaay external_video identifies a saved link, not its media type.
            kind = transport_kinds.get(member['ordinal'], member.get('kind'))
            if index < len(kinds) and kind in {'image', 'video'} and kind != kinds[index]:
                errors.append('member_type:' + str(index))
        if errors:
            result['receipt_discrepancies'].append({'source_key': item['source_key'], 'item_id': identity,
                'errors': errors, 'expected': expected, 'receipt_members': received, 'archived_types': kinds})
    for cid, collection in collections.items():
        current = [m for m in observed['memberships'] if m['collection_id'] == cid]
        previous = [m for m in active.values() if m['collection_id'] == cid]
        current_sequence = [membership_id(m) for m in sorted(current, key=lambda m: m['ordinal'])]
        previous_sequence = [m['identity'] for m in sorted(previous, key=lambda m: (m['ordinal'], m['identity']))]
        ties = len(current) != len({m['ordinal'] for m in current})
        result['collections'].append({'id': cid, 'title': collection['title'], 'parent': collection.get('parent'),
            'source_memberships': len(current), 'server_memberships': len(previous),
            'identities_equal': Counter(current_sequence) == Counter(previous_sequence),
            'unique_source_ordinals': not ties,
            'order_equal': current_sequence == previous_sequence if not ties else None,
            'audit': observed.get('completion', {}).get('collection_audits', {}).get(cid)})
    key_counts = Counter(i['source_key'] for i in items.values())
    result['duplicate_saved_records'] = {key: count for key, count in key_counts.items() if count > 1}
    result['summary'] = {'native_items': len(items), 'unique_posts': len(key_counts),
                         'collections': len(collections), 'memberships': len(members),
                         'receipt_discrepancies': len(result['receipt_discrepancies']),
                         'collections_with_tied_order': sum(not c['unique_source_ordinals'] for c in result['collections'])}
    return result


def pagination_proof(pages):
    issues, previous, seen = [], None, set()
    if not pages:
        return ['no_pages']
    for index, page in enumerate(pages):
        if page['input_cursor_sha256'] != previous:
            issues.append('cursor_chain:' + str(index))
        if not isinstance(page.get('more_available'), bool):
            issues.append('missing_terminal_flag:' + str(index))
        if index < len(pages) - 1 and not page.get('more_available'):
            issues.append('page_after_terminal:' + str(index))
        cursor = page.get('next_cursor_sha256')
        if page.get('more_available') and (cursor is None or cursor in seen):
            issues.append('missing_or_repeated_cursor:' + str(index))
        previous = cursor
        seen.add(cursor)
    if pages[-1].get('more_available') is not False:
        issues.append('no_terminal_page')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--observed', type=Path, action='append', required=True)
    parser.add_argument('--pagination', type=Path)
    parser.add_argument('--yaay-media-kinds', type=Path)
    args = parser.parse_args()
    server = json.loads(args.server.read_text())
    ledger = server.get('ledger', server)
    kinds = json.loads(args.yaay_media_kinds.read_text()) if args.yaay_media_kinds else None
    observations = [json.loads(path.read_text()) for path in args.observed]
    result = {'sources': [compare(ledger, document, kinds if document['source'] == 'yaay' else None)
                          for document in observations]}
    if args.pagination:
        data = json.loads(args.pagination.read_text())
        groups = defaultdict(list)
        for page in data['instagram_pages']:
            groups['instagram:' + page['endpoint']].append(page)
        for page in data['yaay_pages']:
            if page['initial_checkpoint'] and page['include'] == 'active':
                groups['yaay:' + page['feed']].append(page)
        result['pagination'] = {key: {'pages': len(pages), 'issues': pagination_proof(pages)} for key, pages in groups.items()}
        instagram = next((d for d in observations if d['source'] == 'instagram'), None)
        if instagram:
            items = {i['id']: i['source_key'] for i in instagram['items']}
            result['instagram_api_ui'] = {}
            for group, pages in groups.items():
                if not group.startswith('instagram:'):
                    continue
                match = re.search(r'/collection/(\d+)/', group)
                cid = match[1] if match else 'all'
                api = [p['source_key'] for page in pages for p in page['posts']]
                ui = [items[m['item_id']] for m in sorted(instagram['memberships'], key=lambda m: m['ordinal'])
                      if m['collection_id'] == cid]
                result['instagram_api_ui'][cid] = {'api_posts': len(api), 'ui_posts': len(ui),
                    'identities_equal': Counter(api) == Counter(ui), 'order_equal': api == ui,
                    'duplicate_api_ids': [key for key, count in Counter(api).items() if count > 1]}
        result['capture_errors'] = data['errors']
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
