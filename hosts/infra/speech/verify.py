#!/usr/bin/env python3
"""Read-only Infra health/auth checks. Does not download a model or submit audio."""
import sys
import urllib.error
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
from dotenv import parse

base = 'http://192.168.0.110:8092'
try:
    urllib.request.urlopen(base + '/v1/models', timeout=10)
    raise AssertionError('Unauthenticated model API was accepted')
except urllib.error.HTTPError as error:
    assert error.code in (401, 403)
key = dict(parse(Path('/srv/appdata/docker/speech/runtime.env')))['SPEECH_API_KEY']
with urllib.request.urlopen(urllib.request.Request(base + '/health', headers={'Authorization': 'Bearer ' + key}), timeout=10) as response:
    assert response.status == 200
request = urllib.request.Request(base + '/v1/models', headers={'Authorization': 'Bearer ' + key})
with urllib.request.urlopen(request, timeout=20) as response:
    assert response.status == 200
print('Speech health and authenticated API passed; no inference performed')
