#!/usr/bin/env python3
"""PVE: retain only published editorial files/history in production appdata."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


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
    # The publisher's article manifest omits navigation folders. Their generated
    # _index files carry normalized UUIDs; retain only identities present in the
    # published tree, never every non-article entry in the private history ledger.
    for file in (source / 'published/interests').rglob('_index.md'):
        header = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)', file.read_text(), re.S)
        identity = re.findall(r'^id: ([0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12})[ \t]*$',
                              header[1] if header else '', re.M)
        if len(identity) != 1:
            raise ValueError('Published folder lacks a normalized publisher identity')
        ids.add(identity[0])
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
            if file.is_symlink():
                raise ValueError('Published inputs must be regular files')
            os.link(file, target)
    save(stage / 'manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
    save(stage / 'history.json', (json.dumps(history, indent=2) + '\n').encode())
    checksums = {name: digest for name, digest in json.loads((source / 'checksums.json').read_text()).items() if name.startswith('published/')}
    for name in ('manifest.json', 'history.json'):
        checksums[name] = hashlib.sha256((stage / name).read_bytes()).hexdigest()
    revision = hashlib.sha256(json.dumps(checksums, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    save(stage / 'checksums.json', (json.dumps(checksums, indent=2) + '\n').encode())
    target = root / revision
    if not target.exists():
        stage.rename(target)
    else:
        # This newly created temporary tree is disposable; never delete a retained input.
        shutil.rmtree(stage)
    return revision
