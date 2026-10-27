#!/usr/bin/env python3
"""CT110: secure seeded account and create the fixed staging website via API."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
from dotenv import parse

BASE = 'http://192.168.0.110:8090'
ENV = Path('/srv/appdata/docker/observability/runtime.env')


def api(path, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(BASE + path, headers=headers,
                                     data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def login(password):
    return api('/api/auth/login', {'username': 'admin', 'password': password})['token']


def main():
    password = dict(parse(ENV))['BLOG_UMAMI_ADMIN_PASSWORD']
    try:
        token = login(password)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise
        # Only the upstream seeded password can be replaced; an existing
        # independently managed account is never reset by recovery automation.
        token = login('umami')
        api('/api/me/password', {'currentPassword': 'umami', 'newPassword': password}, token)
        token = login(password)
    site = json.loads((Path(__file__).parents[2] / 'staging/blog-observability/website.json').read_text())
    try:
        actual = api('/api/websites/' + site['id'], token=token)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        actual = None
    if actual is None:
        actual = api('/api/websites', site, token)
    if any(actual.get(key) != value for key, value in site.items()):
        raise RuntimeError('Umami website identity differs from the declared staging site')
    print('Umami operator login and private staging website verified; credentials withheld')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # API bodies/tokens/passwords must not escape into automation logs.
        raise SystemExit(f'Umami initialization failed ({type(error).__name__}); inspect privately') from None
