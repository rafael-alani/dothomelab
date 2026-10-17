"""Shared read-only retirement checks for staging producers."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path('/srv/appdata/docker/staging/retired')
PROTOCOL = 1


def retired(repository, root=ROOT):
    repository = re.sub(r'^https://github.com/', '', repository)
    repository = repository.removesuffix('.git').casefold()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]*/[a-z0-9][a-z0-9_.-]*', repository):
        raise ValueError('Invalid repository identity')
    path = root / (hashlib.sha256(repository.encode()).hexdigest() + '.json')
    try:
        value = json.loads(path.read_text())
    except FileNotFoundError:
        return False
    if path.is_symlink() or value.get('version') != 1 or value.get('repository') != repository or value.get('state') not in {'retiring', 'retired', 'purging', 'purged'}:
        raise ValueError('Invalid retirement record')
    return True


def active_apps(path, root=ROOT):
    return {name: app for name, app in json.loads(path.read_text()).items() if not retired(app['repository'], root)}


def retired_hostname(host):
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.rafael\.media', host):
        raise ValueError('Invalid hostname')
    path = Path('/srv/appdata/docker/infra-nginx-proxy-manager/staging-retired-hosts') / (host + '.json')
    return path.exists()
