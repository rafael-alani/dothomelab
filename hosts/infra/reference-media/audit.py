#!/usr/bin/env python3
"""Read-only archive audit; JSON to stdout, bounded progress to stderr.

Run on PVE via SSH. No Archive instance is constructed: SQLite is opened ro.
--probe-videos streams originals through the existing Jellyfin FFprobe in CT112.
It checks stream metadata, not decoding every frame. Calibration is separate.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time


def probe_video(stream):
    # Buffered seek can leave the underlying descriptor past the MP4 header.
    stream.seek(0)
    os.lseek(stream.fileno(), 0, os.SEEK_SET)
    command = ['pct', 'exec', '112', '--', 'docker', 'exec', '-i', 'jellyfin',
               '/usr/lib/jellyfin-ffmpeg/ffprobe', '-v', 'error', '-show_entries',
               'stream=codec_type,codec_name,width,height,duration:format=duration',
               '-of', 'json', 'pipe:0']
    completed = subprocess.run(command, stdin=stream, capture_output=True, timeout=120)
    data = json.loads(completed.stdout or b'{}')
    videos = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
    duration = float(data.get('format', {}).get('duration') or 0)
    return {'returncode': completed.returncode, 'video_streams': videos,
            'duration': duration, 'stderr_bytes': len(completed.stderr)}


def probe_valid(probe):
    return not probe['returncode'] and bool(probe['video_streams']) and probe['duration'] > 0 and not probe['stderr_bytes']


def decode_first_frame(root, asset):
    result = {'id': asset['id'], 'errors': []}
    relative = asset['path']
    if not re.fullmatch(r'objects/[a-f0-9]{64}\.(mp4|webm|mov)', relative):
        result['errors'].append('unsafe_video_path')
        return result
    path = root / relative
    if root.is_symlink() or path.parent.is_symlink() or path.is_symlink():
        result['errors'].append('symlink')
        return result
    try:
        with path.open('rb') as stream:
            command = ['pct', 'exec', '112', '--', 'docker', 'exec', '-i', 'jellyfin',
                       '/usr/lib/jellyfin-ffmpeg/ffmpeg', '-v', 'error', '-i', 'pipe:0',
                       '-map', '0:v:0', '-an', '-frames:v', '1', '-vf', 'scale=16:16',
                       '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1']
            completed = subprocess.run(command, stdin=stream, capture_output=True, timeout=120)
            result.update(returncode=completed.returncode, frame_bytes=len(completed.stdout), stderr_bytes=len(completed.stderr))
            if completed.returncode or len(completed.stdout) != 768 or completed.stderr:
                result['errors'].append('first_frame_decode')
    except Exception as error:
        result['errors'].append(type(error).__name__)
    return result


def verify_asset(root, asset, probe=False):
    result = {'id': asset['id'], 'path': asset['path'], 'errors': []}
    relative = asset['path']
    if not re.fullmatch(r'objects/[a-f0-9]{64}\.(mp4|webm|mov|jpg|jpeg|png|webp)', relative):
        result['errors'].append('unsafe_path')
        return result
    path = root / relative
    if root.is_symlink() or path.parent.is_symlink() or path.is_symlink():
        result['errors'].append('symlink')
        return result
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb', buffering=0) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                result['errors'].append('not_regular')
                return result
            result.update(bytes=info.st_size, mode=oct(stat.S_IMODE(info.st_mode)))
            if info.st_size != asset['bytes'] or info.st_size <= 0:
                result['errors'].append('size_mismatch')
            if info.st_mode & 0o222:
                result['errors'].append('writable')
            result['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            if result['sha256'] != asset['id'] or path.stem != asset['id']:
                result['errors'].append('hash_mismatch')
            stream.seek(0)
            signature = stream.read(16)
            kind = 'video' if path.suffix in {'.mp4', '.mov', '.webm'} else 'image'
            result['kind'] = kind
            if path.suffix in {'.jpg', '.jpeg'} and not signature.startswith(b'\xff\xd8\xff'):
                result['errors'].append('jpeg_signature')
            if path.suffix in {'.mp4', '.mov'} and signature[4:8] != b'ftyp':
                result['errors'].append('mp4_signature')
            if probe and kind == 'video':
                result['probe'] = probe_video(stream)
                if not probe_valid(result['probe']):
                    result['errors'].append('video_probe')
    except Exception as error:
        result['errors'].append(type(error).__name__)
    return result


def ledger(db):
    result = {}
    for table in ('assets', 'collections', 'membership_entries', 'post_assets', 'completed_posts'):
        result[table] = [dict(r) for r in db.execute('SELECT * FROM ' + table)]
    for member in result['membership_entries']:
        member.pop('metadata')
    for receipt in result['completed_posts']:
        receipt['members'] = json.loads(receipt.pop('asset_ids'))
    result['source_items'] = []
    for row in db.execute('SELECT source,id,source_key,metadata FROM source_items'):
        item = dict(row)
        item['members'] = json.loads(item.pop('metadata')).get('carousel_members', [])
        result['source_items'].append(item)
    result['scans'] = []
    for row in db.execute('SELECT id,source,status,received,inventory FROM scans ORDER BY received'):
        scan = dict(row)
        document = json.loads(scan.pop('inventory'))
        scan.update(completion=document.get('completion'), gaps=document.get('gaps'))
        result['scans'].append(scan)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/vault/shared/media/references'))
    parser.add_argument('--database', type=Path, default=Path('/srv/appdata/docker/reference-media/catalog.sqlite'))
    parser.add_argument('--probe-videos', action='store_true')
    parser.add_argument('--decode-first-frames-only', action='store_true', help='Separate video decode pass; does not repeat hashes')
    args = parser.parse_args()
    report = {'started': time.time(), 'probe_requested': args.probe_videos}
    db = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('BEGIN')
    report['sqlite_check'] = [r[0] for r in db.execute('PRAGMA quick_check')]
    report['ledger'] = ledger(db)
    db.close()
    data = report['ledger']
    if args.decode_first_frames_only:
        videos = [a for a in data['assets'] if Path(a['path']).suffix in {'.mp4', '.webm', '.mov'}]
        report['frames'] = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            for result in pool.map(lambda a: decode_first_frame(args.root, a), videos):
                report['frames'].append(result)
                if len(report['frames']) % 100 == 0:
                    print(json.dumps({'decoded': len(report['frames']), 'total': len(videos)}), file=sys.stderr, flush=True)
        report.pop('ledger')
        report['finished'] = time.time()
        print(json.dumps(report))
        return any(r['errors'] for r in report['frames'])
    real_keys = {r['source_key'] for r in data['source_items'] if r['source'] != 'calibration'}
    calibration_keys = {r['source_key'] for r in data['source_items'] if r['source'] == 'calibration'}
    real_assets = {p['asset_id'] for p in data['post_assets'] if p['source_key'] in real_keys}
    calibration_assets = {p['asset_id'] for p in data['post_assets'] if p['source_key'] in calibration_keys} - real_assets
    report['assets'] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda a: verify_asset(args.root, a, args.probe_videos), data['assets']):
            result['calibration'] = result['id'] in calibration_assets
            report['assets'].append(result)
            if len(report['assets']) % 100 == 0:
                print(json.dumps({'checked': len(report['assets']), 'total': len(data['assets'])}), file=sys.stderr, flush=True)
    known = {a['path'] for a in data['assets']}
    report['untracked_object_paths'] = sorted(str(p.relative_to(args.root)) for p in (args.root / 'objects').iterdir()
                                               if str(p.relative_to(args.root)) not in known)
    links = {(p['source_key'], p['ordinal'], p['asset_id']) for p in data['post_assets']}
    receipts = {(r['source_key'], m['ordinal'], m['id']) for r in data['completed_posts'] for m in r['members']}
    report['receipt_links_missing'] = sorted(receipts - links)
    report['links_outside_receipts'] = sorted(links - receipts)
    report['posts_without_receipts'] = sorted(real_keys - {r['source_key'] for r in data['completed_posts']})
    report['summary'] = {'real_posts': len(real_keys), 'real_assets': len(real_assets),
                         'calibration_assets': len(calibration_assets),
                         'real_types': dict(Counter(a.get('kind', 'unknown') for a in report['assets'] if a['id'] in real_assets)),
                         'real_bytes': sum(a.get('bytes', 0) for a in report['assets'] if a['id'] in real_assets),
                         'real_asset_failures': sum(bool(a['errors']) for a in report['assets'] if a['id'] in real_assets),
                         'calibration_asset_failures': sum(bool(a['errors']) for a in report['assets'] if a['id'] in calibration_assets),
                         'asset_failures': sum(bool(a['errors']) for a in report['assets'])}
    report['finished'] = time.time()
    print(json.dumps(report, ensure_ascii=False))
    return bool(report['sqlite_check'] != ['ok'] or report['summary']['asset_failures'] or
                report['untracked_object_paths'] or report['receipt_links_missing'] or
                report['links_outside_receipts'] or report['posts_without_receipts'])


if __name__ == '__main__':
    raise SystemExit(main())
