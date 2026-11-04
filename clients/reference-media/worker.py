#!/usr/bin/env python3
"""Awake-only bounded catch-up: inventory checkpoints, immutable upload receipts."""
import argparse
import copy
import fcntl
import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from collector import open_browser, fresh_context, collect_yaay
from downloader import download, DownloadError
from instagram import advance, atomic_json
from inventory import empty_document
from publish import publish
from transport import Transport


def thumbnail(file, target):
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.new.jpg')
    try:
        subprocess.run(['/opt/homebrew/bin/ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(file),
                        '-frames:v', '1', '-vf', 'scale=480:480:force_original_aspect_ratio=decrease',
                        '-q:v', '5', str(temporary)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=45, check=True)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def submit(transport, document):
    snapshot = copy.deepcopy(document)
    snapshot['scan_id'] = str(uuid.uuid4())
    return transport.inventory(snapshot)


def collection_keys(catalog, collection):
    if not any(c['source'] == 'instagram' and c['id'] == collection and c['active'] for c in catalog['collections']):
        raise ValueError('unknown_active_instagram_collection')
    items = {i['id']: i['source_key'] for i in catalog['items'] if i['source'] == 'instagram'}
    return {items[m['item_id']] for m in catalog['memberships']
            if m['source'] == 'instagram' and m['collection_id'] == collection and m['active']}


def download_yaay(context, members, work):
    files = []
    for member in members:
        parsed = urlsplit(member['url'] or '')
        if parsed.scheme != 'https' or not parsed.hostname or parsed.hostname in {'localhost', '127.0.0.1'}:
            raise ValueError('yaay_member_unavailable')
        response = context.request.get(member['url'], timeout=60000)
        try:
            if not response.ok:
                raise ValueError('yaay_media_unavailable')
            kind = response.headers.get('content-type', '').split(';')[0]
            extensions = {'video/mp4': 'mp4', 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}
            if kind not in extensions or (member['kind'] == 'video' and kind != 'video/mp4'):
                raise ValueError('unsupported_yaay_media')
            file = work / (str(member['ordinal']) + '.' + extensions[kind])
            file.write_bytes(response.body())
            files.append({'file': file, 'ordinal': member['ordinal']})
        finally:
            response.dispose()
    if not files:
        raise ValueError('yaay_media_unavailable')
    return files


def acquire(item, cookies, context, media, work):
    key = item['source_key']
    if key.startswith('instagram:'):
        try:
            return download(item['url'], cookies, work), 'instagram'
        except DownloadError as error:
            if error.reason == 'rate_limited' or not media.get(key):
                raise
            # The same canonical Instagram identity can have a retained Yaay
            # copy even when its original link has disappeared.
    if media.get(key):
        return download_yaay(context, media[key], work), 'yaay'
    raise ValueError('source_media_not_available')


def run(support, batch, collection=None, finish=False):
    state_path = support / 'worker-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'retry': {}, 'issues': []}
    daily = state.get('daily_mode', False)
    now = time.time()
    if not (collection or finish) and daily and now < state.get('next_fetch_after', 0):
        return  # No SSH, browser, source requests or vault writes between daily runs.
    if daily and not (collection or finish):
        # Persist before I/O so failures/restarts cannot create frequent fetches.
        state['next_fetch_after'] = now + 86400
    state['issues'] = []
    state['completed_this_run'] = 0
    state['phase'] = 'scanning'
    state['last_attempt'] = now
    atomic_json(state_path, state)
    config = json.loads((support / 'config.json').read_text())
    vault = Path(config['vault'])
    if not (vault / '.obsidian').is_dir() or vault.is_symlink():
        raise ValueError('local_vault_unavailable')
    transport = Transport(config['host'], support / 'ingest-key')
    transport.request({'action': 'status'})  # Fail before downloading when offline.
    selected_keys = collection_keys(transport.request({'action': 'catalog'}), collection) if collection else None
    def publish_status():
        atomic_json(state_path, state)
        publish(vault, transport.request({'action': 'catalog'}), state)
    media = {}
    with sync_playwright() as p:
        browser = open_browser(p, support / 'browser-profile')
        context = fresh_context(browser)
        cookies = browser.cookies('https://www.instagram.com/')
        try:
            if not collection and (finish or daily or time.time() - state.get('yaay_scan', 0) > 3600):
                try:
                    document, media = collect_yaay(context)
                    submit(transport, document)
                    atomic_json(support / 'yaay-inventory.json', document)
                    if document['status'] == 'complete':
                        state['yaay_scan'] = time.time()
                    else:
                        state['issues'].extend('Yaay: ' + issue for issue in document['gaps'])
                except Exception as error:
                    state['issues'].append('Yaay scan needs attention: ' + type(error).__name__)
                    failed = empty_document('yaay')
                    failed['status'] = 'failed'
                    submit(transport, failed)
            checkpoint = support / 'instagram-scan.json'
            if not collection and (finish or daily or checkpoint.exists() or time.time() - state.get('instagram_scan', 0) > 21600):
                try:
                    document = advance(context, cookies, config['instagram_saved_url'], checkpoint,
                                       page_budget=None if daily or finish else 8, thumbnail_dir=vault / 'References/Thumbnails')
                    submit(transport, document)
                    if document['status'] == 'complete':
                        atomic_json(support / 'instagram-inventory.json', document)
                        checkpoint.unlink()
                        state['instagram_scan'] = time.time()
                except Exception as error:
                    state['issues'].append('Instagram scan needs attention: ' + type(error).__name__)
                    failed = empty_document('instagram')
                    failed['status'] = 'failed'
                    submit(transport, failed)
            state['phase'] = f'acquiring Instagram collection {collection}' if collection else 'backfill / catch-up'
            publish_status()
            pending = transport.request({'action': 'pending'})
            selected = [] if not finish and time.time() < state.get('acquisition_after', 0) else [item for item in pending if (selected_keys is None or item['source_key'] in selected_keys)
                and (item['source_key'].startswith('instagram:') or media.get(item['source_key']))
                and (finish or state['retry'].get(item['source_key'], {}).get('after', 0) <= time.time())]
            if not finish:
                selected = selected[:batch]
            failures = 0
            for item in selected:
                key = item['source_key']
                work = support / 'downloads' / hashlib.sha256(key.encode()).hexdigest()
                work.mkdir(parents=True, exist_ok=True)
                try:
                    files, via = acquire(item, cookies, context, media, work)
                    receipt = []
                    for member in files:
                        asset = transport.put(member['file'])
                        transport.request({'action': 'link', 'source_key': key, 'ordinal': member['ordinal'], 'asset_id': asset['id']})
                        receipt.append({'id': asset['id'], 'ordinal': member['ordinal'], 'via': via})
                        try:
                            thumbnail(member['file'], vault / 'References/Thumbnails' / (asset['id'] + '.jpg'))
                        except Exception:
                            state['issues'].append('One thumbnail could not be generated; original retained.')
                    transport.request({'action': 'complete_post', 'source_key': key, 'assets': receipt})
                    # No permanent local full-media cache. Delete only the exact
                    # temporary members acknowledged in this completed receipt.
                    for member in files:
                        member['file'].unlink()
                    if not any(work.iterdir()):
                        work.rmdir()
                    state['retry'].pop(key, None)
                    state['completed_this_run'] = state.get('completed_this_run', 0) + 1
                except Exception as error:
                    failures += 1
                    attempts = state['retry'].get(key, {}).get('attempts', 0) + 1
                    state['retry'][key] = {'attempts': attempts, 'after': time.time() + min(7 * 86400, 3600 * 2 ** min(attempts, 8)), 'error': type(error).__name__}
                    if isinstance(error, DownloadError):
                        state['retry'][key].update(reason=error.reason, details=error.details)
                    # An explicit finish attempts each original once, but stops
                    # on access/rate failures rather than hammering the source.
                    if finish and (not isinstance(error, DownloadError) or error.reason in {'rate_limited', 'source_access_denied'}):
                        failures = max(failures, 2)
                    elif finish:
                        failures = 0
                atomic_json(state_path, state)
                if failures >= 2:
                    state['acquisition_after'] = time.time() + 3600
                    state['issues'].append('Acquisition paused for one hour after two failures; prior media retained.')
                    break
            remaining = transport.request({'action': 'pending'})
            # Failed originals remain retryable without keeping initial polling alive.
            if (not collection and not daily and state.get('yaay_scan') and state.get('instagram_scan')
                    and not checkpoint.exists() and not state['issues']
                    and all(item['source_key'] in state['retry'] for item in remaining)):
                state.update(daily_mode=True, next_fetch_after=time.time() + 86400)
            state['phase'] = 'waiting for daily catch-up' if state.get('daily_mode') else 'waiting for next awake backfill batch'
            state['pending_posts'] = len(remaining)
            state['retry_posts'] = len(state['retry'])
            state['last_success'] = time.time()
            publish_status()
        finally:
            context.close()
            browser.close()
    print(json.dumps({k: state.get(k) for k in ('phase', 'pending_posts', 'retry_posts', 'issues')}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support', type=Path, required=True)
    parser.add_argument('--batch', type=int, default=12)
    parser.add_argument('--instagram-collection', help='Acquire only current members of this exact collection ID, without rescanning or changing the daily due time. Retry cooldowns still apply.')
    parser.add_argument('--finish-backfill', action='store_true', help='Explicitly finish inventory pagination and attempt every pending original once, including prior failures. Stop on source access/rate errors; preserve the daily schedule.')
    args = parser.parse_args()
    os.umask(0o077)
    with (args.support / 'worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            run(args.support, args.batch, args.instagram_collection, args.finish_backfill)
        except Exception as error:
            # Never log an exception message, URL, browser profile or cookies.
            print(json.dumps({'phase': 'needs_attention_or_offline', 'error': type(error).__name__}), flush=True)
            try:
                config = json.loads((args.support / 'config.json').read_text())
                vault = Path(config['vault'])
                catalog = json.loads((vault / 'References/Catalog.json').read_text())
                state = json.loads((args.support / 'worker-state.json').read_text()) if (args.support / 'worker-state.json').exists() else {}
                state.update(phase='needs attention or offline', issues=['Last attempt failed: ' + type(error).__name__ + '. Previous inventory and media are retained.'])
                atomic_json(args.support / 'worker-state.json', state)
                publish(vault, catalog, state)
            except Exception:
                pass
            raise SystemExit(1) from None


if __name__ == '__main__':
    main()
