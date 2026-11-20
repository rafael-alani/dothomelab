#!/usr/bin/env python3
"""Archive and verify one stopped preview, then remove its runtime and live data."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

PREVIEWS = Path('/srv/appdata/docker/staging/previews')
RECOVERY = Path('/srv/appdata/docker/staging/branchline/preview-recovery')


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def digest(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def mountpoints():
    return [Path(line.split()[4].replace('\\040', ' ').replace('\\134', '\\'))
            for line in Path('/proc/self/mountinfo').read_text().splitlines()]


def archive_entries(directory):
    for root, dirs, files in os.walk(directory, followlinks=False):
        if Path(root) == directory:
            dirs[:] = [name for name in dirs if name not in ['build-core', 'build-skills']]
        for name in sorted(dirs + files):
            file = Path(root) / name
            relative = file.relative_to(directory).as_posix()
            # MySQL recreates this socket link; it is not database data.
            if relative == 'mysql/mysql.sock' and file.is_symlink():
                continue
            if file.is_symlink() or not (file.is_dir() or file.is_file()):
                raise ValueError('Unsupported recovery entry: ' + relative)
            yield file, relative


def archive_preview(directory, identifier):
    RECOVERY.mkdir(mode=0o700, parents=True, exist_ok=True)
    if RECOVERY.is_symlink():
        raise ValueError('Recovery directory must not be a symlink')
    archive = RECOVERY / (identifier + '.tar.gz')
    receipt = RECOVERY / (identifier + '.json')
    if archive.is_symlink() or receipt.is_symlink():
        raise ValueError('Recovery files must not be symlinks')
    previous = json.loads(receipt.read_text()) if receipt.exists() else None
    if previous and (not archive.is_file() or digest(archive) != previous['sha256']):
        raise RuntimeError('Recovery archive checksum mismatch; live data retained')
    entries = list(archive_entries(directory))
    if not archive.exists():
        partial = archive.with_suffix('.partial')
        descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as output:
            with tarfile.open(fileobj=output, mode='w:gz', compresslevel=1) as saved:
                for file, relative in entries:
                    saved.add(file, arcname=relative, recursive=False)
            output.flush()
            os.fsync(output.fileno())
        partial.replace(archive)
    archived_files = set()
    with tarfile.open(archive, 'r:gz') as saved:
        for member in saved:
            relative = Path(member.name)
            if relative.is_absolute() or '..' in relative.parts or not (member.isdir() or member.isfile()):
                raise ValueError('Unsafe recovery archive entry')
            file = directory / relative
            if member.isfile():
                archived_files.add(member.name)
                with saved.extractfile(member) as stream:
                    expected = hashlib.file_digest(stream, 'sha256').hexdigest()
                # A retry may follow partial removal. Any surviving data must match.
                if not previous and not file.is_file():
                    raise RuntimeError('Recovery archive is incomplete')
                if file.exists() and (not previous or relative.parts[0] in ['mysql', 'seed-state']):
                    if file.is_symlink() or digest(file) != expected:
                        raise RuntimeError('Recovery byte verification failed; live data retained')
    required_files = {relative for file, relative in entries if file.is_file() and
                      (not previous or Path(relative).parts[0] in ['mysql', 'seed-state'])}
    if not required_files <= archived_files:
        raise RuntimeError('Recovery archive is missing files; live data retained')
    if not previous:
        descriptor = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            json.dump({'id': identifier, 'sha256': digest(archive), 'files': len(archived_files),
                       'verifiedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}, output)
            output.flush()
            os.fsync(output.fileno())
    descriptor = os.open(RECOVERY, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def cleanup(environ=os.environ):
    identifier = environ['BRANCHLINE_PREVIEW_ID']
    if not re.fullmatch(r'[a-f0-9]{10}-[a-f0-9]{8}', identifier):
        raise ValueError('Invalid preview identity')
    root = PREVIEWS.resolve(strict=True)
    directory = Path(environ['BRANCHLINE_PREVIEW_DIR'])
    if not directory.is_absolute() or directory != root / identifier or directory.is_symlink():
        raise ValueError('Cleanup target is not the exact preview directory')
    if directory.exists() and directory.resolve(strict=True) != directory:
        raise ValueError('Cleanup target resolves outside the preview directory')
    project = 'bl-' + identifier
    if environ.get('COMPOSE_PROJECT_NAME') != project:
        raise ValueError('Preview project identity mismatch')
    if docker('ps', '--all', '--quiet', '--filter', 'label=com.docker.compose.project=' + project):
        raise RuntimeError('Preview still has containers; Compose down must finish first')

    # A foreign container must not keep using artifacts selected for removal.
    containers = docker('ps', '--all', '--quiet').split()
    if containers:
        for line in docker('inspect', '--format', '{{json .Mounts}}', *containers).splitlines():
            for mount in json.loads(line):
                source = Path(mount.get('Source', '/'))
                if source == directory or directory in source.parents:
                    raise RuntimeError('A container still mounts this preview')

    for target in [directory / name for name in ['build-core', 'build-skills']]:
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            raise ValueError('Build cleanup target is not a regular directory')
    if any(mount == directory or directory in mount.parents for mount in mountpoints()):
        raise ValueError('Preview cleanup target contains a mount')

    archive_preview(directory, identifier)

    # Remove exact tags only: never force removal or prune shared parent images.
    for image in ['branchline-skills:' + identifier, 'branchline-labracore:' + identifier]:
        if docker('image', 'ls', '--quiet', image):
            docker('image', 'rm', '--no-prune', image)
    if directory.exists():
        shutil.rmtree(directory)


if __name__ == '__main__':
    cleanup()
