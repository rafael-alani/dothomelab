#!/usr/bin/env python3
"""Guest: ensure the declared local model is downloaded; do not run inference."""
import sys
import urllib.error
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
from dotenv import parse

MODEL = 'deepdml/faster-whisper-large-v3-turbo-ct2'
key = dict(parse(Path('/srv/appdata/docker/speech/runtime.env')))['SPEECH_API_KEY']
url = 'http://192.168.0.110:8092/v1/models/' + MODEL
headers = {'Authorization': 'Bearer ' + key}
try:
    urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20).close()
except urllib.error.HTTPError as error:
    if error.code != 404:
        raise SystemExit('Cannot inspect the local model: HTTP ' + str(error.code))
    try:
        urllib.request.urlopen(urllib.request.Request(url, headers=headers, method='POST'), timeout=1800).close()
    except Exception as error:
        raise SystemExit('Local model download failed: ' + type(error).__name__)
print('Local model installed:', MODEL)
