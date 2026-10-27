#!/usr/bin/env python3
"""Measure real Mac-save-to-HTTPS publication using one owned disposable article."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--vault', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
identity = str(uuid.uuid4())
slug = 'publication-timing-' + identity[:8]
file = args.vault / 'Blog/art-corner/songs' / (slug + '.md')
route = '/art-corner/songs/' + slug
origins = {'staging': 'https://blog.staging.rafael.media', 'production': 'https://rafael.ink'}
results = []

def save(status, marker):
    file.write_text(f'---\nid: {identity}\nkind: article\nstatus: {status}\npublishedAt: "2026-10-27"\ndescription: ""\n---\n\nTemporary publication timing test. {marker}\n')

def observe(environment, marker, present, started):
    while time.monotonic() - started < 300:
        request = urllib.request.Request(origins[environment] + route,
            headers={'User-Agent': 'blog-healthcheck', 'Cache-Control': 'no-cache'})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                status, body = response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            status, body = error.code, ''
        except (TimeoutError, urllib.error.URLError):
            status, body = 0, ''
        if (present and status == 200 and marker in body) or (not present and status == 404):
            return {'environment': environment, 'seconds': round(time.monotonic() - started, 3), 'status': status}
        time.sleep(0.3)
    raise TimeoutError(environment + ' did not converge: ' + route)

try:
    with file.open('x'):
        pass
    for label, status in [('publish', 'published'), ('edit-1', 'published'), ('edit-2', 'published'),
                          ('draft', 'draft'), ('republish', 'published'), ('delete', None)]:
        marker = slug + '-' + label
        saved_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        started = time.monotonic()
        if status:
            save(status, marker)
        else:
            file.unlink()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(observe, environment, marker, status is not None and
                (environment == 'staging' or status == 'published'), started) for environment in origins]
            observed = [future.result() for future in futures]
        result = {'change': label, 'savedAt': saved_at, 'observed': observed}
        results.append(result)
        args.output.write_text(json.dumps({'route': route, 'results': results}, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        time.sleep(2)
finally:
    # Only this run's newly-created article is removed; no authored note is selected.
    if file.exists() and identity in file.read_text():
        file.unlink()
