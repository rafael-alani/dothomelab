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


def published_input(source, root):
    manifest = [row for row in json.loads((source / 'manifest.json').read_text()) if row['status'] == 'published']
    ids = {row['id'] for row in manifest}
    history = {key: value for key, value in json.loads((source / 'history.json').read_text()).items() if key in ids}
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='input-', dir=root))
    shutil.copytree(source / 'published', stage / 'published')
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (stage / 'history.json').write_text(json.dumps(history, indent=2) + '\n')
    checksums = {str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(stage.rglob('*')) if p.is_file()}
    revision = hashlib.sha256(json.dumps(checksums, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    (stage / 'checksums.json').write_text(json.dumps(checksums, indent=2) + '\n')
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
    # Use the guest identity for new files; do not recursively repair existing state.
    os.setgid(100000)
    os.setuid(100000)
    revision = published_input(source, root)
    temporary = root / 'current.next'
    temporary.write_text(json.dumps({'revision': revision, 'source_revision': source.name}) + '\n')
    temporary.replace(root / 'current.json')
    print('Prepared published-only editorial input ' + revision)


if __name__ == '__main__':
    main()
