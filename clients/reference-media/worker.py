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
from downloader import download
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


def run(support, batch):
    config = json.loads((support / 'config.json').read_text())
    vault = Path(config['vault'])
    if not (vault / '.obsidian').is_dir() or vault.is_symlink():
        raise ValueError('local_vault_unavailable')
    transport = Transport(config['host'], support / 'ingest-key')
    transport.request({'action': 'status'})  # Fail before downloading when offline.
    state_path = support / 'worker-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'retry': {}, 'issues': []}
    state['issues'] = []
    state['completed_this_run'] = 0
    state['phase'] = 'scanning'
    state['last_attempt'] = time.time()
    atomic_json(state_path, state)
    def publish_status():
        atomic_json(state_path, state)
        publish(vault, transport.request({'action': 'catalog'}), state)
    media = {}
    with sync_playwright() as p:
        browser = open_browser(p, support / 'browser-profile')
        context = fresh_context(browser)
        cookies = browser.cookies('https://www.instagram.com/')
        try:
            if time.time() - state.get('yaay_scan', 0) > 3600:
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
            if checkpoint.exists() or time.time() - state.get('instagram_scan', 0) > 21600:
                try:
                    document = advance(context, cookies, config['instagram_saved_url'], checkpoint)
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
            state['phase'] = 'backfill / catch-up'
            publish_status()
            pending = transport.request({'action': 'pending'})
            selected = [] if time.time() < state.get('acquisition_after', 0) else [item for item in pending if state['retry'].get(item['source_key'], {}).get('after', 0) <= time.time()][:batch]
            failures = 0
            for item in selected:
                key = item['source_key']
                work = support / 'downloads' / hashlib.sha256(key.encode()).hexdigest()
                work.mkdir(parents=True, exist_ok=True)
                try:
                    if key.startswith('instagram:'):
                        files = download(item['url'], cookies, work)
                    elif key in media and media[key]:
                        # The observed UI supplied these temporary URLs. Only
                        # HTTPS public transport is accepted, never local URLs.
                        files = []
                        for member in media[key]:
                            parsed = urlsplit(member['url'])
                            if parsed.scheme != 'https' or not parsed.hostname or parsed.hostname in {'localhost', '127.0.0.1'}:
                                raise ValueError('invalid_source_transport')
                            response = context.request.get(member['url'], timeout=60000)
                            if not response.ok:
                                raise ValueError('yaay_media_unavailable')
                            kind = response.headers.get('content-type', '').split(';')[0]
                            extensions = {'video/mp4': 'mp4', 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}
                            if kind not in extensions:
                                raise ValueError('unsupported_yaay_media')
                            file = work / (str(member['ordinal']) + '.' + extensions[kind])
                            file.write_bytes(response.body())
                            response.dispose()
                            files.append({'file': file, 'ordinal': member['ordinal']})
                    else:
                        raise ValueError('source_media_not_available')
                    receipt = []
                    for member in files:
                        asset = transport.put(member['file'])
                        transport.request({'action': 'link', 'source_key': key, 'ordinal': member['ordinal'], 'asset_id': asset['id']})
                        receipt.append({'id': asset['id'], 'ordinal': member['ordinal']})
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
                atomic_json(state_path, state)
                if failures >= 2:
                    state['acquisition_after'] = time.time() + 3600
                    state['issues'].append('Acquisition paused for one hour after two failures; prior media retained.')
                    break
            state['phase'] = 'waiting for next awake catch-up'
            state['pending_posts'] = len(transport.request({'action': 'pending'}))
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
    args = parser.parse_args()
    os.umask(0o077)
    with (args.support / 'worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            run(args.support, args.batch)
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
