"""Verify and materialize immutable blog exports; never mount the vault in staging."""
import hashlib
import json
import re
import shutil
from pathlib import Path


def snapshot(root: Path, revision: str) -> Path:
    root = root.resolve()
    if not re.fullmatch(r'[0-9a-f]{64}', revision):
        raise ValueError('Invalid editorial revision')
    source = root / revision
    if source.is_symlink():
        raise ValueError('Unsafe editorial snapshot path')
    checksums = json.loads((source / 'checksums.json').read_text())
    # JSON.stringify's compact encoding is the export revision contract.
    if hashlib.sha256(json.dumps(checksums, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest() != revision:
        raise ValueError('Editorial manifest digest mismatch')
    for name, digest in checksums.items():
        file = source / name
        if Path(name).is_absolute() or '..' in Path(name).parts or file.resolve() != file.absolute():
            raise ValueError('Unsafe editorial path')
        if not re.fullmatch(r'[0-9a-f]{64}', digest) or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError('Editorial file digest mismatch')
    actual = {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    if actual != set(checksums) | {'checksums.json'} or any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Unexpected file in editorial snapshot')
    return source


def materialize(base: Path, source: Path, target: Path, mode: str = 'preview') -> Path:
    if mode not in ('preview', 'published'):
        raise ValueError('Editorial mode must be preview or published')
    revision = source.name
    snapshot(source.parent, revision)
    marker = target / '.editorial-complete'
    if marker.exists():
        if marker.read_text() != revision + ':' + mode:
            raise ValueError('Build context belongs to another editorial revision')
        return target
    # A failed preparation is retained, never broadly cleaned up or reused.
    if target.exists():
        raise ValueError('Incomplete editorial context retained; inspect it before retrying')
    shutil.copytree(base, target, ignore=shutil.ignore_patterns('.git', 'node_modules', 'build', '.astro', '.cache', '.react-router', 'generated', 'test-results', 'playwright-report', '.impeccable'))
    # The verified export is the complete editorial tree. Git content is only
    # a standalone seed; merging it here resurrects deleted folders and notes.
    for name in ('interests', 'obsidian'):
        destination = target / 'content' / name
        if destination.exists():
            shutil.rmtree(destination)  # newly copied build context, never the vault or base
        incoming = source / mode / name
        if incoming.is_dir():
            shutil.copytree(incoming, destination)
        else:
            destination.mkdir(parents=True)
            if name == 'obsidian':
                (destination / 'collections.json').write_text('[]\n')
    incoming_history = json.loads((source / 'history.json').read_text())
    history_path = target / 'content' / 'route-history.json'
    history = json.loads(history_path.read_text())
    for identity, entry in incoming_history.items():
        old = history.get(identity, {})
        history[identity] = {'current': entry['current'], 'paths': sorted(set(old.get('paths', []) + entry['paths']))}
    history_path.write_text(json.dumps(history, indent=2) + '\n')
    marker.write_text(revision + ':' + mode)
    return target
