#!/usr/bin/env python3
"""Restore the exact enrolled Contentflow image from canonical recovery artifacts."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = Path('/srv/appdata/docker/contentflow')


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    if run('findmnt', '-n', '-o', 'SOURCE', '-T', str(ROOT)) != 'rpool/appdata/docker':
        raise RuntimeError('Contentflow canonical appdata is not mounted')
    release = json.loads((HERE / 'release.json').read_text())
    recovery = ROOT / 'recovery' / release['commit']
    for name, key in [('image.tar.gz', 'image_archive_sha256'), ('source.tar.gz', 'source_archive_sha256')]:
        with (recovery / name).open('rb') as handle:
            if hashlib.file_digest(handle, 'sha256').hexdigest() != release[key]:
                raise RuntimeError(f'Contentflow {name} recovery hash mismatch')
    for name in ['deployment.env', 'secrets/api-token']:
        if not (ROOT / name).is_file():
            raise RuntimeError(f'Missing protected Contentflow input: {name}')
    for name in ['state', 'example-media']:
        if not (ROOT / name).is_dir():
            raise RuntimeError(f'Missing Contentflow directory: {name}')
    tag = 'contentflow:' + release['commit']
    result = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', tag],
                            text=True, capture_output=True)
    if result.returncode:
        legacy = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', 'contentflow:local'],
                                text=True, capture_output=True)
        if legacy.returncode == 0 and legacy.stdout.strip() != release['image_id']:
            raise RuntimeError('Unenrolled Contentflow image found; refusing to replace its tag')
        subprocess.run(['docker', 'load', '-i', str(recovery / 'image.tar.gz')], check=True, stdout=subprocess.DEVNULL)
        if run('docker', 'image', 'inspect', '--format', '{{.Id}}', 'contentflow:local') != release['image_id']:
            raise RuntimeError('Loaded Contentflow image identity does not match enrollment')
        run('docker', 'tag', 'contentflow:local', tag)
    if run('docker', 'image', 'inspect', '--format', '{{.Id}}', tag) != release['image_id']:
        raise RuntimeError('Contentflow image identity drifted')
    run('docker', 'network', 'inspect', 'n8n_default')
    print('Contentflow recovery hashes, image identity, durable inputs and n8n network verified')


if __name__ == '__main__':
    main()
