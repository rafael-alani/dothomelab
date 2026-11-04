#!/usr/bin/env python3
"""Restricted SSH ingestion endpoint; immutable objects, retained inventory history.

One JSON header line followed by an optional exact-size body. No shell, arbitrary
paths, source credentials, network fetches, or deletion operation.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
import transcripts

EXTENSIONS = {'mp4', 'webm', 'mov', 'jpg', 'jpeg', 'png', 'webp'}
SOURCES = {'instagram', 'yaay', 'calibration'}


class Archive:
    def __init__(self, root, state):
        self.root, self.state = Path(root), Path(state)
        if not self.root.is_dir() or not self.state.is_dir():
            raise ValueError('archive_offline')
        self.objects = self.root / 'objects'
        self.objects.mkdir(exist_ok=True)
        if self.objects.is_symlink():
            raise ValueError('invalid_archive')
        self.db = sqlite3.connect(self.state / 'catalog.sqlite', timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          PRAGMA journal_mode=WAL;
          PRAGMA foreign_keys=ON;
          CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, bytes INTEGER NOT NULL, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS source_items (
            source TEXT, id TEXT, source_key TEXT NOT NULL, url TEXT,
            metadata TEXT NOT NULL, last_seen REAL NOT NULL,
            PRIMARY KEY(source,id));
          CREATE TABLE IF NOT EXISTS post_assets (
            source_key TEXT, ordinal INTEGER, asset_id TEXT REFERENCES assets(id),
            PRIMARY KEY(source_key,ordinal,asset_id));
          CREATE TABLE IF NOT EXISTS collections (
            source TEXT, id TEXT, parent TEXT, title TEXT NOT NULL, ordinal INTEGER,
            active INTEGER NOT NULL, last_scan TEXT, PRIMARY KEY(source,id));
          CREATE TABLE IF NOT EXISTS membership_entries (
            source TEXT, identity TEXT, collection_id TEXT, item_id TEXT, ordinal INTEGER,
            active INTEGER NOT NULL, last_scan TEXT, metadata TEXT NOT NULL,
            PRIMARY KEY(source,identity));
          CREATE TABLE IF NOT EXISTS completed_posts (
            source_key TEXT PRIMARY KEY, asset_ids TEXT NOT NULL, completed REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY, source TEXT, status TEXT, received REAL,
            inventory TEXT NOT NULL);
        ''')
        transcripts.initialize(self.db)

    def put(self, header, stream):
        digest, ext, size = header['sha256'], header['extension'], header['bytes']
        if not re.fullmatch('[a-f0-9]{64}', digest) or ext not in EXTENSIONS:
            raise ValueError('invalid_asset')
        if not isinstance(size, int) or not 0 < size <= 4 * 1024**3:
            raise ValueError('invalid_size')
        descriptor, temporary = tempfile.mkstemp(prefix='.incoming-', dir=self.objects)
        try:
            checksum = hashlib.sha256()
            remaining = size
            with os.fdopen(descriptor, 'wb') as target:
                while remaining:
                    data = stream.read(min(1024 * 1024, remaining))
                    if not data:
                        raise ValueError('interrupted_upload')
                    target.write(data)
                    checksum.update(data)
                    remaining -= len(data)
                target.flush()
                os.fsync(target.fileno())
            if checksum.hexdigest() != digest:
                raise ValueError('checksum_mismatch')
            # Content identity also deduplicates equivalent filename extensions.
            existing = self.db.execute('SELECT path FROM assets WHERE id=?', (digest,)).fetchone()
            relative = existing['path'] if existing else f'objects/{digest}.{ext}'
            destination = self.root / relative
            if destination.is_symlink():
                raise ValueError('invalid_asset_path')
            if destination.exists():
                with destination.open('rb') as existing_file:
                    actual_digest = hashlib.file_digest(existing_file, 'sha256').hexdigest()
                if destination.stat().st_size != size or actual_digest != digest:
                    raise ValueError('existing_asset_corrupt')
            else:
                os.chmod(temporary, 0o444)
                # link is atomic and cannot overwrite a previous immutable object.
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    raise ValueError('concurrent_upload_retry') from None
            with self.db:
                self.db.execute('INSERT OR IGNORE INTO assets VALUES(?,?,?,?)', (digest, relative, size, time.time()))
            return {'id': digest, 'path': relative, 'bytes': size}
        finally:
            os.unlink(temporary)

    def inventory(self, document):
        source, scan = document['source'], document['scan_id']
        if source not in SOURCES or not re.fullmatch('[a-zA-Z0-9-]{1,80}', scan):
            raise ValueError('invalid_scan')
        collections, items, memberships = (document[key] for key in ('collections', 'items', 'memberships'))
        complete = document.get('status') == 'complete'
        if document.get('status') not in {'complete', 'partial', 'needs_sign_in', 'rate_limited', 'failed'}:
            raise ValueError('invalid_status')
        collection_ids = {c['id'] for c in collections}
        item_ids = {item['id'] for item in items}
        if len(collection_ids) != len(collections) or len(item_ids) != len(items):
            raise ValueError('duplicate_ids')
        if complete:
            proof = document.get('completion', {})
            if not all(proof.get(key) is True for key in ('authenticated', 'pagination_complete', 'roots_complete')) or proof.get('visited_collections') != len(collections):
                raise ValueError('missing_completion_proof')
        parents = {c['id']: c.get('parent') for c in collections}
        for identity in parents:
            seen = set()
            parent = identity
            while parent is not None:
                if parent in seen or parent not in parents:
                    raise ValueError('invalid_hierarchy')
                seen.add(parent)
                parent = parents[parent]
        for membership in memberships:
            if membership['collection_id'] not in collection_ids or membership['item_id'] not in item_ids:
                raise ValueError('dangling_membership')
        serialized = json.dumps(document, ensure_ascii=False, sort_keys=True)
        previous = self.db.execute('SELECT inventory FROM scans WHERE id=?', (scan,)).fetchone()
        if previous:
            if previous['inventory'] != serialized:
                raise ValueError('scan_id_conflict')
            return self.status()  # Retry after a lost acknowledgement is idempotent.
        with self.db:
            for collection in collections:
                self.db.execute('''INSERT INTO collections VALUES(?,?,?,?,?,1,?)
                  ON CONFLICT(source,id) DO UPDATE SET parent=excluded.parent,
                  title=excluded.title,ordinal=excluded.ordinal,active=1,last_scan=excluded.last_scan''',
                  (source, collection['id'], collection.get('parent'), collection['title'], collection['ordinal'], scan))
            for item in items:
                key = item['source_key']
                if not re.fullmatch(r'(instagram:[A-Za-z0-9_-]+|yaay:[A-Za-z0-9_-]+|calibration:[a-f0-9]+)', key):
                    raise ValueError('invalid_source_key')
                self.db.execute('''INSERT INTO source_items VALUES(?,?,?,?,?,?)
                  ON CONFLICT(source,id) DO UPDATE SET source_key=excluded.source_key,
                  url=excluded.url,metadata=excluded.metadata,last_seen=excluded.last_seen''',
                  (source, item['id'], key, item.get('url'), json.dumps(item.get('metadata', {}), ensure_ascii=False), time.time()))
            for membership in memberships:
                identity = membership.get('source_membership_id') or (membership['collection_id'] + ':' + membership['item_id'])
                self.db.execute('''INSERT INTO membership_entries VALUES(?,?,?,?,?,1,?,?)
                  ON CONFLICT(source,identity) DO UPDATE SET collection_id=excluded.collection_id,
                  item_id=excluded.item_id,ordinal=excluded.ordinal,active=1,
                  last_scan=excluded.last_scan,metadata=excluded.metadata''',
                  (source, identity, membership['collection_id'], membership['item_id'], membership['ordinal'], scan,
                   json.dumps({k: v for k, v in membership.items() if k not in {'collection_id', 'item_id', 'ordinal'}})))
            if complete:
                self.db.execute('UPDATE collections SET active=0 WHERE source=? AND last_scan<>?', (source, scan))
                self.db.execute('UPDATE membership_entries SET active=0 WHERE source=? AND last_scan<>?', (source, scan))
            self.db.execute('INSERT INTO scans VALUES(?,?,?,?,?)', (scan, source, document['status'], time.time(), serialized))
        return self.status()

    def link(self, header):
        if not re.fullmatch(r'(instagram:[A-Za-z0-9_-]+|yaay:[A-Za-z0-9_-]+|calibration:[a-f0-9]+)', header['source_key']):
            raise ValueError('invalid_source_key')
        if not isinstance(header['ordinal'], int) or header['ordinal'] < 0:
            raise ValueError('invalid_ordinal')
        if not self.db.execute('SELECT 1 FROM assets WHERE id=?', (header['asset_id'],)).fetchone():
            raise ValueError('missing_asset')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO post_assets VALUES(?,?,?)', (header['source_key'], header['ordinal'], header['asset_id']))
        return {'linked': True}

    def pending(self):
        return [dict(row) for row in self.db.execute('''SELECT s.source_key, min(s.url) AS url
            FROM source_items s LEFT JOIN completed_posts c ON c.source_key=s.source_key
            WHERE c.source_key IS NULL AND s.url IS NOT NULL GROUP BY s.source_key''')]

    def complete_post(self, header):
        assets = header['assets']
        if not isinstance(assets, list) or not assets or len(assets) > 100:
            raise ValueError('invalid_completion')
        for member in assets:
            if not self.db.execute('SELECT 1 FROM post_assets WHERE source_key=? AND ordinal=? AND asset_id=?',
                                   (header['source_key'], member['ordinal'], member['id'])).fetchone():
                raise ValueError('missing_carousel_member')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO completed_posts VALUES(?,?,?)',
                            (header['source_key'], json.dumps(assets, sort_keys=True), time.time()))
        return {'completed': True}

    def status(self):
        counts = {table: self.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                  for table in ('assets', 'source_items', 'collections', 'membership_entries', 'completed_posts', 'scans')}
        counts['memberships'] = counts.pop('membership_entries')
        latest = self.db.execute('''SELECT source,status,received FROM scans s
            WHERE received=(SELECT max(received) FROM scans WHERE source=s.source)''').fetchall()
        return {'counts': counts, 'sources': [dict(row) for row in latest]}

    def catalog(self):
        collections = [dict(row) for row in self.db.execute('SELECT * FROM collections ORDER BY source,ordinal,id')]
        scans = {}
        for collection in collections:
            scan = collection['last_scan']
            if scan not in scans:
                row = self.db.execute('SELECT inventory FROM scans WHERE id=?', (scan,)).fetchone()
                scans[scan] = json.loads(row['inventory']).get('completion', {}).get('collection_audits', {}) if row else {}
            if collection['id'] in scans[scan]:
                collection['audit'] = scans[scan][collection['id']]
        by_id = {(c['source'], c['id']): c for c in collections}
        def label(source, identity):
            parts, seen = [], set()
            while identity and (source, identity) in by_id and identity not in seen:
                seen.add(identity)
                collection = by_id[(source, identity)]
                parts.append(collection['title'])
                identity = collection['parent']
            return ' / '.join([source.title()] + list(reversed(parts)))
        assets = []
        for asset in self.db.execute('SELECT * FROM assets ORDER BY created'):
            item = dict(asset)
            origins = [dict(row) for row in self.db.execute('''SELECT DISTINCT s.source,s.id,s.source_key,s.url,s.metadata,p.ordinal
                FROM source_items s JOIN post_assets p ON s.source_key=p.source_key WHERE p.asset_id=?''', (item['id'],))]
            memberships = [dict(row) for row in self.db.execute('''SELECT DISTINCT m.* FROM membership_entries m
                JOIN source_items s ON s.source=m.source AND s.id=m.item_id
                JOIN post_assets p ON p.source_key=s.source_key WHERE p.asset_id=?''', (item['id'],))]
            for origin in origins:
                origin['metadata'] = json.loads(origin['metadata'])
            item.update(origins=origins, memberships=memberships,
                        title=next((o['metadata']['title'] for o in origins if o['metadata'].get('title')), item['id'][:12]),
                        collections=sorted({label(m['source'], m['collection_id']) for m in memberships}))
            assets.append(item)
        items = [dict(row) for row in self.db.execute('SELECT * FROM source_items')]
        for item in items:
            item['metadata'] = json.loads(item['metadata'])
        entries = [dict(row) for row in self.db.execute('SELECT * FROM membership_entries ORDER BY source,collection_id,ordinal,identity')]
        acquisitions = [{'source_key': row['source_key'], 'status': 'archived',
                         'members': json.loads(row['asset_ids'])}
                        for row in self.db.execute('SELECT source_key,asset_ids FROM completed_posts')]
        return {'schema': 1, 'assets': assets, 'items': items, 'memberships': entries,
                'collections': collections, 'acquisitions': acquisitions, **self.status()}


def serve(archive, reader, writer):
    line = reader.readline(65537)
    if len(line) > 65536:
        raise ValueError('header_too_large')
    header = json.loads(line)
    action = header.get('action')
    if action == 'put':
        result = archive.put(header, reader)
    elif action == 'inventory':
        size = header.get('bytes', 0)
        if not isinstance(size, int) or not 0 < size <= 64 * 1024**2:
            raise ValueError('invalid_inventory_size')
        body = reader.read(size)
        if len(body) != size:
            raise ValueError('interrupted_inventory')
        result = archive.inventory(json.loads(body))
    elif action == 'link':
        result = archive.link(header)
    elif action == 'pending':
        result = archive.pending()
    elif action == 'complete_post':
        result = archive.complete_post(header)
    elif action == 'catalog':
        result = archive.catalog()
    elif action == 'status':
        result = archive.status()
    elif action == 'transcripts':
        result = transcripts.read(archive, header.get('asset_ids'), header.get('model', transcripts.MODEL))
    elif action == 'request_transcripts':
        result = transcripts.request(archive, header.get('asset_ids'), header.get('model', transcripts.MODEL))
    else:
        raise ValueError('unsupported_operation')
    writer.write(json.dumps({'ok': True, 'result': result}, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    os.umask(0o077)
    # Fixed deployment paths, never supplied by an SSH client/environment.
    try:
        import signal
        signal.alarm(900)
        import subprocess
        for mount, dataset in [('/vault/shared', 'vault/shared'), ('/srv/appdata/docker', 'rpool/appdata/docker')]:
            if subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '-T', mount], text=True).strip() != dataset:
                raise ValueError('archive_mount_offline')
        instance = Archive('/vault/shared/media/references', '/srv/appdata/docker/reference-media')
        serve(instance, sys.stdin.buffer, sys.stdout)
    except Exception as error:
        # Errors can contain private metadata or SQLite values; emit only class.
        print(json.dumps({'ok': False, 'error': type(error).__name__}))
        sys.exit(1)
