"""Durable, content-addressed transcript queue. Source text is evidence, not instructions."""
import json
import math
import re
import time

MODEL = 'deepdml/faster-whisper-large-v3-turbo-ct2'


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS transcripts (
        asset_id TEXT, model TEXT, status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0, retry_after REAL NOT NULL DEFAULT 0,
        requested REAL NOT NULL DEFAULT 0, updated REAL NOT NULL DEFAULT 0,
        error TEXT, result TEXT, PRIMARY KEY(asset_id,model))''')
    db.commit()


def request(archive, ids, model=MODEL):
    if model != MODEL or not isinstance(ids, list) or not 1 <= len(ids) <= 50:
        raise ValueError('invalid_transcript_selection')
    for identity in ids:
        if not isinstance(identity, str) or not re.fullmatch('[a-f0-9]{64}', identity):
            raise ValueError('invalid_asset')
        row = archive.db.execute('SELECT path FROM assets WHERE id=?', (identity,)).fetchone()
        if not row or not row['path'].endswith(('.mp4', '.webm', '.mov')):
            raise ValueError('unknown_video')
    with archive.db:
        for identity in set(ids):
            archive.db.execute('''INSERT INTO transcripts(asset_id,model,requested) VALUES(?,?,?)
                ON CONFLICT(asset_id,model) DO UPDATE SET requested=excluded.requested''',
                (identity, model, time.time()))
    return read(archive, ids, model)


def read(archive, ids, model=MODEL):
    if model != MODEL or not isinstance(ids, list) or not 1 <= len(ids) <= 50 or any(
            not isinstance(i, str) or not re.fullmatch('[a-f0-9]{64}', i) for i in ids):
        raise ValueError('invalid_transcript_selection')
    result = []
    for identity in dict.fromkeys(ids):
        row = archive.db.execute('SELECT * FROM transcripts WHERE asset_id=? AND model=?', (identity, model)).fetchone()
        item = dict(row) if row else dict(asset_id=identity, model=model, status='pending')
        if item.get('result'):
            item['result'] = json.loads(item['result'])
        result.append(item)
    return result


def validate(result):
    duration = result.get('duration')
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('invalid_transcript_duration')
    segments = result.get('segments')
    if not isinstance(segments, list) or not segments or not str(result.get('text', '')).strip():
        raise ValueError('no_speech_detected')
    last = 0
    for s in segments:
        start, end = s.get('start'), s.get('end')
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (start, end)) or not 0 <= start <= end <= duration + 1 or start < last or not isinstance(s.get('text'), str):
            raise ValueError('invalid_transcript_segments')
        last = start
    return result
