#!/usr/bin/env python3
"""Read-only coverage and optional full-content audit of a split photo tar."""
import argparse
import bisect
import collections
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import tarfile
import time

class Parts(io.RawIOBase):
    def __init__(self, paths):
        self.paths = paths
        self.starts = [0]
        for path in paths:
            self.starts.append(self.starts[-1] + path.stat().st_size)
        self.pos = 0
        self.handle = None
        self.index = None
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.starts[-1] + offset
        if pos < 0: raise ValueError('negative seek')
        self.pos = pos
        return pos
    def read(self, size=-1):
        if size < 0: raise ValueError('unbounded archive reads are forbidden')
        blocks = []
        while size and self.pos < self.starts[-1]:
            index = bisect.bisect_right(self.starts, self.pos) - 1
            if self.index != index:
                if self.handle: self.handle.close()
                self.handle = self.paths[index].open('rb')
                self.index = index
            self.handle.seek(self.pos - self.starts[index])
            block = self.handle.read(min(size, self.starts[index + 1] - self.pos))
            if not block: raise EOFError('archive part changed or became truncated')
            blocks.append(block)
            self.pos += len(block)
            size -= len(block)
        return b''.join(blocks)
    def close(self):
        if self.handle: self.handle.close()
        super().close()

def normalize(name):
    while name.startswith('./'): name = name[2:]
    if name in ['', '.']: return ''
    if name.startswith('/') or '..' in name.split('/'): raise ValueError('unsafe archive path')
    return name.rstrip('/')

def inventory(source):
    if not source.is_dir() or source.is_symlink():
        raise ValueError('source must be an existing real directory')
    def fail(error):
        raise error
    entries = {}
    for parent, dirs, files in os.walk(source, followlinks=False, onerror=fail):
        for name in dirs + files:
            p = Path(parent) / name
            st = p.lstat()
            relative = p.relative_to(source).as_posix()
            if stat.S_ISREG(st.st_mode): kind, detail = 'file', st.st_size
            elif stat.S_ISLNK(st.st_mode): kind, detail = 'symlink', os.readlink(p)
            elif stat.S_ISDIR(st.st_mode): continue
            else: kind, detail = 'special', stat.S_IFMT(st.st_mode)
            entries[relative] = (kind, detail, st.st_mtime_ns, st.st_ctime_ns, st.st_ino, st.st_dev)
    return entries

def compare_contents(source, paths):
    # GNU tar checks payloads without extracting over the source. Diagnostics may
    # contain private filenames, so only counters/statuses leave this process.
    with tempfile.TemporaryFile() as diagnostics:
        with subprocess.Popen(['cat', *map(str, paths)], stdout=subprocess.PIPE,
                              stderr=diagnostics) as reader:
            try:
                comparison = subprocess.run(
                    ['tar', '--compare', '--file=-', '--directory=' + str(source)],
                    stdin=reader.stdout, stdout=diagnostics, stderr=subprocess.STDOUT)
            finally:
                reader.stdout.close()
            reader_status = reader.wait()
        return {'tar_exit_code': comparison.returncode,
                'reader_exit_code': reader_status,
                'diagnostic_bytes': diagnostics.tell()}


def audit(source, stage, contents=False):
    started = time.time()
    before = inventory(source)
    paths = sorted(stage.glob('archive.tar.part-*'))
    if not paths or any(p.is_symlink() or not p.is_file() for p in paths): raise ValueError('missing or unsafe archive parts')
    if [p.name for p in paths] != [f'archive.tar.part-{i:05d}' for i in range(len(paths))]: raise ValueError('part sequence has gaps')
    initial = [(p.stat().st_size, p.stat().st_mtime_ns) for p in paths]
    archived = {}
    duplicate = 0
    with Parts(paths) as stream, tarfile.open(fileobj=stream, mode='r:') as archive:
        for entry in archive:
            name = normalize(entry.name)
            if not name or entry.isdir(): continue
            if name in archived: duplicate += 1
            if entry.isreg(): item = ('file', entry.size)
            elif entry.islnk(): item = ('hardlink', normalize(entry.linkname))
            elif entry.issym(): item = ('symlink', entry.linkname)
            else: item = ('special', entry.type.decode('ascii', errors='replace'))
            archived[name] = item
    def resolved(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen: raise ValueError('cyclic hardlink')
        seen.add(name)
        kind, value = archived[name]
        return resolved(value, seen) if kind == 'hardlink' else (kind, value)
    records = {name: resolved(name) for name in archived}
    expected = {name: value[:2] for name, value in before.items()}
    comparison = compare_contents(source, paths) if contents else None
    after = inventory(source)
    missing = expected.keys() - records.keys()
    extra = records.keys() - expected.keys()
    mismatch = [name for name in expected.keys() & records.keys() if expected[name] != records[name]]
    changed = before != after
    archive_changed = initial != [(p.stat().st_size, p.stat().st_mtime_ns) for p in paths]
    counts = collections.Counter(value[0] for value in expected.values())
    result = {
        'passed': not any([missing, extra, mismatch, duplicate, changed, archive_changed]),
        'source_files': counts['file'],
        'source_file_bytes': sum(value[1] for value in expected.values() if value[0] == 'file'),
        'source_symlinks': counts['symlink'], 'source_special_entries': counts['special'],
        'archive_files': sum(value[0] == 'file' for value in records.values()),
        'archive_parts': len(paths), 'archive_bytes': sum(size for size, mtime in initial),
        'missing_paths': len(missing), 'unexpected_paths': len(extra),
        'type_or_size_mismatches': len(mismatch), 'duplicate_archive_paths': duplicate,
        'source_changed_during_audit': changed, 'archive_changed_during_audit': archive_changed,
        'elapsed_seconds': round(time.time() - started, 1),
        'scope': 'Every non-directory source path and regular-file size; payload hashes are not compared.'
    }
    if comparison is not None:
        result['content_comparison'] = comparison
        result['passed'] = result['passed'] and all(
            comparison[key] == 0 for key in ('tar_exit_code', 'reader_exit_code'))
        result['scope'] = 'Every non-directory source path/size plus GNU tar full-content comparison.'
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('stage', type=Path)
    parser.add_argument('--contents', action='store_true',
                        help='Also compare every archived file with the live source; requires GNU tar.')
    args = parser.parse_args()
    try:
        result = audit(args.source.absolute(), args.stage.absolute(), args.contents)
    except Exception as error:
        result = {'passed': False, 'error_type': type(error).__name__}
    print(json.dumps(result, sort_keys=True), flush=True)
    raise SystemExit(0 if result['passed'] else 1)
