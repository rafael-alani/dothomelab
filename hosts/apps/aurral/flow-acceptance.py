#!/usr/bin/env python3
"""Generate a bounded real flow, or verify its authenticated audio playback.

Run on CT112 after loading the deployment dotenv. Creation is explicit and
idempotent; normal verification never generates tracks or starts downloads.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append('/opt/dothomelab/hosts/apps/aurral')
from configure import BASE, request

NAME = 'Homelab Library Blend'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create', action='store_true', help='Create and run a three-track flow once')
    parser.add_argument('--verify', action='store_true', help='Require generated tracks and working audio')
    args = parser.parse_args()
    token = request('/api/auth/login', method='POST', payload={
        'username': os.environ['AURRAL_ADMIN_USERNAME'],
        'password': os.environ['AURRAL_ADMIN_PASSWORD'],
    })['token']
    status = request('/api/playlists/status', token=token)
    flows = [f for f in status['flows'] if f['name'] == NAME]
    if len(flows) > 1:
        raise RuntimeError('Ambiguous acceptance flow; refusing to mutate')
    if not flows and args.create:
        data = Path('/srv/appdata/docker/aurral/data')
        backup = data / 'recovery' / f'pre-generated-flow-{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}.db'
        backup.parent.mkdir(exist_ok=True)
        with sqlite3.connect(f'file:{data / "aurral.db"}?mode=ro', uri=True) as src:
            with sqlite3.connect(backup) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Pre-flow SQLite backup failed integrity check')
        backup.chmod(0o600)
        flow = request('/api/playlists/flows', method='POST', token=token, payload={
            'name': NAME, 'mix': {'mix': 100}, 'size': 3,
            'deepDive': False, 'recentListening': False, 'recordHistory': False,
            'autoDownload': True, 'scheduleDays': [5], 'scheduleTime': '00:00',
        })['flow']
        if flow.get('enabled'):
            raise RuntimeError('New acceptance flow unexpectedly has a schedule enabled')
        result = request(f'/api/playlists/start/{flow["id"]}', method='POST',
                         payload={'limit': 3}, token=token)
        print(json.dumps({'created': flow['id'], 'queued': result.get('queued'), 'backup': str(backup)}))
        return 0
    if not flows:
        raise RuntimeError('Generated acceptance flow is absent')
    flow = flows[0]
    stats = status['flowStats'].get(flow['id'], {})
    print(json.dumps({'id': flow['id'], 'name': NAME, 'scheduled': flow.get('enabled'),
                      'generated_at': flow.get('lastRunAt'), 'stats': stats,
                      'queue': status.get('operationQueue')}))
    if not args.verify:
        return 0
    if not flow.get('lastRunAt') or not stats.get('done'):
        raise RuntimeError('Flow has not generated playable tracks yet')
    result = request(f'/api/playlists/jobs/{flow["id"]}', token=token)
    jobs = result if isinstance(result, list) else result['jobs']
    done = [j for j in jobs if j.get('status') == 'done']
    if not done:
        raise RuntimeError('Generated flow has no completed track jobs')
    for job in done:
        req = urllib.request.Request(f'{BASE}/api/playlists/stream/{job["id"]}', headers={
            'Authorization': f'Bearer {token}', 'Range': 'bytes=0-4095',
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read(4096)
            if response.status != 206 or len(body) != 4096:
                raise RuntimeError('Authenticated flow audio range did not return 4096 bytes')
        print(f'PASS generated track audio: {job["id"]}')
    print(f'PASS real generated flow and authenticated playback: {len(done)} track(s)')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError) as error:
        print(f'FAIL {error}', file=sys.stderr)
        raise SystemExit(1)
