#!/usr/bin/env python3
"""Protect generated docs, then archive reviewed conflicts without exposing content."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

WAYPOINT_START = 'updateWaypoint(t,e){return l(this,null,function*(){'
WAYPOINT_GUARD = 'if(this.ignorePath(t.path))return;'
WAYPOINT_SHA = '502c013ed54626751378db3408b42bf09c163f6437ec664c907fd87a7dfe4723'
BLOCK = re.compile(rb'%%\s*Begin Waypoint\s*%%.*?%%\s*End Waypoint\s*%%', re.S | re.I)
CONFLICT = re.compile(r'\.sync-conflict-\d{8}-\d{6}-[A-Z0-9]+')
PREFIX = b'<!-- Generated repository documentation; edit the source repository. -->'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def confined(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Unsafe relative path')
    if path.resolve() != path.absolute() or not path.resolve().is_relative_to(root):
        raise ValueError('Symlinks are not supported')
    return path


def read(path):
    return path.read_bytes() if path.exists() else None


def atomic(path, data, mode=0o600):
    fd, name = tempfile.mkstemp(prefix='.sync-repair-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def put_blob(recovery, data):
    if data is None:
        return None
    digest = sha(data)
    path = recovery / (digest + '.blob')
    if not path.exists():
        atomic(path, data)
    if path.read_bytes() != data:
        raise ValueError('Recovery blob verification failed')
    return digest


def blob(recovery, digest):
    if digest is None:
        return None
    if not re.fullmatch('[a-f0-9]{64}', digest):
        raise ValueError('Invalid blob name')
    data = (recovery / (digest + '.blob')).read_bytes()
    if sha(data) != digest:
        raise ValueError('Recovery blob verification failed')
    return data


def save_plan(root, recovery, changes):
    if recovery.exists() or recovery.is_relative_to(root):
        raise ValueError('Use a new private recovery directory outside the vault')
    recovery.mkdir(parents=True, mode=0o700)
    entries = []
    for relative, after, reason in changes:
        path = confined(root, relative)
        before = read(path)
        if before == after:
            continue
        entries.append(dict(path=relative, before=put_blob(recovery, before),
                            after=put_blob(recovery, after), reason=reason,
                            mode=path.stat().st_mode & 0o777 if path.exists() else 0o600))
    plan = dict(version=1, root=str(root), entries=entries)
    atomic(recovery / 'plan.json', (json.dumps(plan, indent=2) + '\n').encode())
    return plan


def apply(recovery, restore=None):
    plan = json.loads((recovery / 'plan.json').read_text())
    if plan['version'] != 1:
        raise ValueError('Unsupported plan version')
    root = Path(plan['root']).resolve(strict=True)
    entries = [e for e in plan['entries'] if restore is None or e['path'] == restore]
    if restore is not None and len(entries) != 1:
        raise ValueError('Select one exact manifest path to restore')
    staged = []
    for entry in entries:
        before, after = (blob(recovery, entry[k]) for k in ('before', 'after'))
        expected, desired = (before, after) if restore is None else (after, before)
        path = confined(root, entry['path'])
        if read(path) != expected:
            raise ValueError('File changed since planning; no changes applied')
        staged.append((path, expected, desired, entry['mode']))
    for path, expected, desired, mode in staged:
        if read(path) != expected:
            raise ValueError('Concurrent edit; stopped, recovery copies retained')
        if desired is None:
            path.unlink()
        else:
            atomic(path, desired, mode)
    return len(staged)


def protect(root):
    changes = []
    relative = '.obsidian/plugins/folder-notes/data.json'
    settings = json.loads(confined(root, relative).read_text())
    excluded = next((x for x in settings['excludeFolders'] if x.get('path') == '05. Docs' and x.get('type') == 'folder'), None)
    if excluded is None:
        excluded = dict(settings['excludeFolderDefaultSettings'], id='dothomelab-generated-docs',
                        path='05. Docs', position=len(settings['excludeFolders']))
        settings['excludeFolders'].append(excluded)
    excluded.update(subFolders=True, disableAutoCreate=True, disableSync=True)
    changes.append((relative, (json.dumps(settings, indent=2) + '\n').encode(), 'Exclude generated docs from Folder Notes writers'))
    relative = '.obsidian/plugins/waypoint/data.json'
    settings = json.loads(confined(root, relative).read_text())
    for pattern in [r'^05\. Docs(?:/|$)', r'\.sync-conflict-']:
        if pattern not in settings['ignorePaths']:
            settings['ignorePaths'].append(pattern)
    changes.append((relative, (json.dumps(settings, indent=2) + '\n').encode(), 'Exclude generated docs and conflict copies from Waypoint'))
    relative = '.obsidian/plugins/waypoint/main.js'
    original = confined(root, relative).read_text()
    patched = WAYPOINT_START + WAYPOINT_GUARD
    if patched not in original:
        if sha(original.encode()) != WAYPOINT_SHA or original.count(WAYPOINT_START) != 1:
            raise ValueError('Waypoint changed; review its writer before patching')
        changes.append((relative, original.replace(WAYPOINT_START, patched).encode(), 'Honor Waypoint exclusions at the shared writer'))
    return changes


def non_navigation(data):
    data = BLOCK.sub(b'', data)
    data = re.sub(rb'<%\s*tp\.file\.cursor\(1\)\s*%>', b'', data)
    return re.sub(rb'%%\s*Waypoint\s*%%', b'', data, flags=re.I).strip()


def cleanup(root):
    changes, restored = [], {}
    for path in sorted(root.rglob('*sync-conflict*')):
        if path.is_dir():
            continue
        relative = str(path.relative_to(root))
        data = confined(root, relative).read_bytes()
        # Only restore text into an otherwise empty generated document. All other
        # unique versions stay in private recovery blobs; never merge old settings.
        if relative.startswith('05. Docs/') and data.startswith(PREFIX):
            target = CONFLICT.sub('', relative)
            canonical = confined(root, target)
            current = read(canonical)
            if current is not None and not non_navigation(current) and non_navigation(data):
                if target in restored and non_navigation(restored[target]) != non_navigation(data):
                    raise ValueError('Conflicting document bodies need manual reconciliation')
                restored[target] = clean_links(data)
        changes.append((relative, None, 'Archived conflict or derived conflict cache'))
    for target, data in restored.items():
        changes.insert(0, (target, data, 'Recover document text from conflict into navigation-only canonical file'))
    # Remove dead conflict links only inside generated navigation blocks.
    for path in sorted(root.rglob('*.md')):
        if 'sync-conflict' in path.name or '.stversions' in path.parts:
            continue
        relative = str(path.relative_to(root))
        if relative in restored:
            continue
        data = confined(root, relative).read_bytes()
        after = clean_links(data)
        if after != data:
            changes.append((relative, after, 'Remove deleted conflict links from generated navigation'))
    return changes


def clean_links(data):
    return BLOCK.sub(lambda m: b''.join(line for line in m[0].splitlines(keepends=True)
                                      if b'.sync-conflict-' not in line), data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['protect', 'plan', 'apply', 'restore'])
    parser.add_argument('--vault', type=Path)
    parser.add_argument('--recovery', type=Path, required=True)
    parser.add_argument('--path', help='One exact manifest path, for restore only')
    args = parser.parse_args()
    recovery = args.recovery.resolve()
    if args.command in {'apply', 'restore'}:
        if args.command == 'restore' and not args.path:
            parser.error('restore needs --path')
        print(json.dumps({'changed': apply(recovery, args.path if args.command == 'restore' else None)}))
    else:
        if not args.vault:
            parser.error('--vault is required')
        root = args.vault.resolve(strict=True)
        if not (root / '.obsidian').is_dir():
            parser.error('Not an existing Obsidian vault')
        plan = save_plan(root, recovery, protect(root) if args.command == 'protect' else cleanup(root))
        print(json.dumps({'planned': len(plan['entries']), 'recovery': str(recovery),
                          'deletions': sum(e['after'] is None for e in plan['entries'])}))


if __name__ == '__main__':
    main()
