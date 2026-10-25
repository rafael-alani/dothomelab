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
    shutil.copytree(base, target, ignore=shutil.ignore_patterns('.git', 'node_modules', 'build', '.react-router'))
    interests = target / 'content' / 'interests'
    for file in (source / mode / 'interests').rglob('*'):
        if not file.is_file():
            continue
        destination = interests / file.relative_to(source / mode / 'interests')
        if destination.exists() and destination.name != '_index.md':
            raise ValueError('Vault article collides with repository content')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, destination)
    history_path = target / 'content' / 'route-history.json'
    history = json.loads(history_path.read_text())
    for identity, entry in json.loads((source / 'history.json').read_text()).items():
        old = history.get(identity, {})
        history[identity] = {'current': entry['current'], 'paths': sorted(set(old.get('paths', []) + entry['paths']))}
    history_path.write_text(json.dumps(history, indent=2) + '\n')
    marker.write_text(revision + ':' + mode)
    return target
