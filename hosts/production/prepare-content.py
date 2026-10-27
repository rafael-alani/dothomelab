#!/usr/bin/env python3
"""PVE: select published content without rehashing or copying unchanged media."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'blog'))
from content import published_input


def main():
    if not Path('/etc/pve').is_dir():
        raise RuntimeError('Run on PVE')
    source_root = Path('/srv/appdata/docker/staging/blog/editorial')
    exported = json.loads((source_root / 'current.json').read_text())
    source = source_root / exported['revision']
    root = Path('/srv/appdata/docker/production/blog/editorial')
    # Source belongs to the exporter UID; only newly created destination files
    # receive the production guest identity. Existing/staging owners stay intact.
    revision = published_input(source, root, owner=(100000, 100000))
    temporary = root / 'current.next'
    temporary.write_text(json.dumps({**exported, 'revision': revision, 'source_revision': source.name}) + '\n')
    os.chown(temporary, 100000, 100000)
    temporary.chmod(0o600)
    temporary.replace(root / 'current.json')
    print('Prepared published-only editorial input ' + revision)


if __name__ == '__main__':
    main()
