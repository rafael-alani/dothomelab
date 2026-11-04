#!/usr/bin/env python3
"""Compare a sanitized source observation with the archive; optionally submit one collection.

Observation JSON: source, collection {id,title}, items (normalized inventory
items), ordered source_keys, grid_keys, pages, pagination_complete, observed_at.
It contains no cookies, CDN URLs or credentials. Never certifies the whole source.
"""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
from inventory import empty_document
from instagram import atomic_json
from publish import publish
from transport import Transport


def reconcile(catalog, observation):
    if observation['source'] != 'instagram' or observation['pagination_complete'] is not True:
        raise ValueError('source_observation_incomplete')
    keys = observation['source_keys']
    if not keys or len(set(keys)) != len(keys) or keys != observation['grid_keys']:
        raise ValueError('source_grid_order_mismatch')
    items = {i['source_key']: i for i in observation['items']}
    if set(items) != set(keys) or sum(observation['pages']) != len(keys):
        raise ValueError('source_identity_or_page_count_mismatch')
    cid = observation['collection']['id']
    current = {(i['source'], i['id']): i['source_key'] for i in catalog['items']}
    before = {current[(m['source'], m['item_id'])] for m in catalog['memberships']
              if m['source'] == 'instagram' and m['collection_id'] == cid and m['active']}
    assets = {}
    for asset in catalog['assets']:
        for origin in asset['origins']:
            assets.setdefault(origin['source_key'], set()).add(asset['id'])
    receipts = {a['source_key'] for a in catalog.get('acquisitions', []) if a['status'] == 'archived'}
    report = [{'position': n + 1, 'source_key': key, 'id': items[key]['id'],
               'media': [m['kind'] for m in items[key]['metadata'].get('carousel_members', [])],
               'archived_files': len(assets.get(key, [])),
               'acquisition': 'archived' if key in receipts else 'partial' if key in assets else 'pending',
               'previously_member': key in before} for n, key in enumerate(keys)]
    document = empty_document('instagram')
    collection = next((c for c in catalog['collections'] if c['source'] == 'instagram' and c['id'] == cid), None)
    if not collection:
        raise ValueError('unknown_collection')
    document['collections'] = [{k: collection[k] for k in ('id', 'title', 'ordinal', 'parent')}]
    document['items'] = [copy.deepcopy(items[key]) for key in keys]
    document['memberships'] = [{'collection_id': cid, 'item_id': items[key]['id'], 'ordinal': n} for n, key in enumerate(keys)]
    document['completion'] = {'method': 'operator-source-api-and-visible-grid',
                              'collection_audits': {cid: {'ui_posts': len(keys), 'api_posts': len(keys),
                                'ui_only': [], 'api_only': [], 'order': 'source_collection_grid',
                                'checked_at': observation['observed_at']}}}
    return document, report, sorted(before - set(keys))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--support', type=Path, required=True)
    p.add_argument('--observed', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    os.umask(0o077)
    with (args.support / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = json.loads((args.support / 'config.json').read_text())
        transport = Transport(config['host'], args.support / 'ingest-key')
        catalog = transport.request({'action': 'catalog'})
        observation = json.loads(args.observed.read_text())
        document, report, absent = reconcile(catalog, observation)
        atomic_json(args.report, {'posts': report, 'absent_from_source': absent, 'observed_at': observation['observed_at']})
        if args.apply:
            # Partial source submission adds/refreshes only this collection.
            # Retiring absent records still requires a full inventory.
            transport.inventory(document)
            state = json.loads((args.support / 'worker-state.json').read_text())
            publish(Path(config['vault']), transport.request({'action': 'catalog'}), state)
        print(json.dumps({'posts': len(report), 'new_members': sum(not r['previously_member'] for r in report),
                          'with_media': sum(r['archived_files'] > 0 for r in report),
                          'absent_members_retained': len(absent), 'applied': args.apply}))


if __name__ == '__main__':
    main()
