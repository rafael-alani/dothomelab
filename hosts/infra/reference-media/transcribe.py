#!/usr/bin/env python3
"""PVE worker: upload immutable videos to Infra; retain transcript receipts locally."""
import argparse
import fcntl
import http.client
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from archive import Archive
from transcripts import MODEL, validate


def transcribe(file, base, key):
    boundary = uuid.uuid4().hex
    fields = {'model': MODEL, 'response_format': 'verbose_json', 'timestamp_granularities[]': 'segment'}
    prefix = ''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()).encode()
    prefix += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
    suffix = f'\r\n--{boundary}--\r\n'.encode()
    url = urlsplit(base)
    connection = (http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection)(url.hostname, url.port, timeout=1800)
    try:
        connection.putrequest('POST', url.path.rstrip('/') + '/audio/transcriptions')
        connection.putheader('Authorization', 'Bearer ' + key)
        connection.putheader('Content-Type', 'multipart/form-data; boundary=' + boundary)
        connection.putheader('Content-Length', str(len(prefix) + file.stat().st_size + len(suffix)))
        connection.endheaders(prefix)
        with file.open('rb') as source:
            while chunk := source.read(1024 * 1024):
                connection.send(chunk)
        connection.send(suffix)
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError('speech_http_' + str(response.status))
        body = response.read(16 * 1024**2 + 1)
        if len(body) > 16 * 1024**2:
            raise ValueError('transcript_too_large')
        return validate(json.loads(body))
    finally:
        connection.close()


def run(archive, config, limit):
    db = archive.db
    # Only fully archived posts are eligible; incomplete carousel uploads wait.
    db.execute('''INSERT OR IGNORE INTO transcripts(asset_id,model)
        SELECT DISTINCT a.id,? FROM assets a JOIN post_assets p ON a.id=p.asset_id
        JOIN completed_posts c ON c.source_key=p.source_key
        WHERE a.path LIKE '%.mp4' OR a.path LIKE '%.webm' OR a.path LIKE '%.mov' ''', (MODEL,))
    db.execute("UPDATE transcripts SET status='pending' WHERE status='running'")  # Exclusive process lock proves prior owner exited.
    db.commit()
    for _ in range(limit):
        row = db.execute('''SELECT t.*,a.path FROM transcripts t JOIN assets a ON a.id=t.asset_id
            WHERE t.model=? AND t.status!='ready' AND t.retry_after<=?
            ORDER BY (t.requested>0) DESC,t.requested DESC,t.attempts,a.created LIMIT 1''', (MODEL, time.time())).fetchone()
        if not row:
            return
        db.execute("UPDATE transcripts SET status='running',updated=? WHERE asset_id=? AND model=?", (time.time(), row['asset_id'], MODEL)); db.commit()
        started = time.time()
        try:
            file = archive.root / row['path']
            if file.is_symlink() or file.resolve().parent != archive.objects.resolve():
                raise ValueError('invalid_archive_path')
            result = transcribe(file, config['url'], config['key'])
            result['elapsed_seconds'] = round(time.time() - started, 2)
            result['provider'] = 'local-speaches'
            db.execute("UPDATE transcripts SET status='ready',result=?,error=NULL,updated=? WHERE asset_id=? AND model=?",
                       (json.dumps(result), time.time(), row['asset_id'], MODEL))
            print(json.dumps(dict(asset_id=row['asset_id'], status='ready', seconds=result['elapsed_seconds'])), flush=True)
        except Exception as error:
            attempts = row['attempts'] + 1
            db.execute("UPDATE transcripts SET status='retry',attempts=?,retry_after=?,error=?,updated=? WHERE asset_id=? AND model=?",
                       (attempts, time.time() + min(86400, 300 * 2**min(attempts, 8)), type(error).__name__, time.time(), row['asset_id'], MODEL))
            print(json.dumps(dict(asset_id=row['asset_id'], status='retry', error=type(error).__name__)), flush=True)
        db.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=4)
    args = parser.parse_args()
    os.umask(0o077)
    state = Path('/srv/appdata/docker/reference-media')
    with (state / 'transcribe.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        config = json.loads((Path(os.environ['CREDENTIALS_DIRECTORY']) / 'speech.json').read_text())
        archive = Archive('/vault/shared/media/references', state)
        try:
            run(archive, config, args.limit)
        finally:
            archive.db.close()


if __name__ == '__main__':
    main()
