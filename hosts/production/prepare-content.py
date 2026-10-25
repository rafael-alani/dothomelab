#!/usr/bin/env python3
"""PVE: retain only published editorial files/history in production appdata."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'staging'))
import editorial


def published_input(source, root, owner=None):
    def directory(path):
        if not path.exists():
            path.mkdir(mode=0o700)
            if owner:
                os.chown(path, *owner)

    def save(path, data):
        path.write_bytes(data)
        path.chmod(0o600)
        if owner:
            os.chown(path, *owner)

    manifest = [row for row in json.loads((source / 'manifest.json').read_text()) if row['status'] == 'published']
    ids = {row['id'] for row in manifest}
    history = {key: value for key, value in json.loads((source / 'history.json').read_text()).items() if key in ids}
    directory(root)
    if root.is_symlink() or (owner and root.stat().st_uid != owner[0]):
        raise RuntimeError('Production editorial ownership/type differs; refusing repair')
    stage = Path(tempfile.mkdtemp(prefix='input-', dir=root))
    if owner:
        os.chown(stage, *owner)
    directory(stage / 'published')
    for file in sorted((source / 'published').rglob('*')):
        target = stage / 'published' / file.relative_to(source / 'published')
        if file.is_dir():
            directory(target)
        else:
            save(target, file.read_bytes())
    save(stage / 'manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
    save(stage / 'history.json', (json.dumps(history, indent=2) + '\n').encode())
    checksums = {str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(stage.rglob('*')) if p.is_file()}
    revision = hashlib.sha256(json.dumps(checksums, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    save(stage / 'checksums.json', (json.dumps(checksums, indent=2) + '\n').encode())
    target = root / revision
    if not target.exists():
        stage.rename(target)
    else:
        # This newly created temporary tree is disposable; never delete a retained input.
        shutil.rmtree(stage)
    editorial.snapshot(root, revision)
    return revision


def main():
    if not Path('/etc/pve').is_dir():
        raise RuntimeError('Run on PVE')
    source_root = Path('/srv/appdata/docker/staging/blog/editorial')
    source = editorial.snapshot(source_root, json.loads((source_root / 'current.json').read_text())['revision'])
    root = Path('/srv/appdata/docker/production/blog/editorial')
    # Source belongs to the exporter UID; only newly created destination files
    # receive the production guest identity. Existing/staging owners stay intact.
    revision = published_input(source, root, owner=(100000, 100000))
    temporary = root / 'current.next'
    temporary.write_text(json.dumps({'revision': revision, 'source_revision': source.name}) + '\n')
    os.chown(temporary, 100000, 100000)
    temporary.chmod(0o600)
    temporary.replace(root / 'current.json')
    print('Prepared published-only editorial input ' + revision)


if __name__ == '__main__':
    main()
