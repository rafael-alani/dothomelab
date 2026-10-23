#!/usr/bin/env python3
"""Copy one explicitly selected canonical song into an immutable private preview."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def checksum(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage_track(source: Path, destination: Path, title: str, artist: str) -> Path:
    digest = checksum(source)
    target = destination / digest[:12]
    metadata = {'title': title, 'artist': artist, 'src': '/listening/audio.mp3', 'preview': True}
    if target.exists():
        if (json.loads((target / 'track.json').read_text()) != metadata or
                checksum(target / 'audio.mp3') != digest):
            raise ValueError('Existing preview differs; preserve it and choose a new destination')
        return target
    target.mkdir(parents=True, mode=0o755)
    shutil.copyfile(source, target / 'audio.mp3')
    (target / 'audio.mp3').chmod(0o644)
    (target / 'track.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (target / 'track.json').chmod(0o644)
    if checksum(target / 'audio.mp3') != digest:
        raise ValueError('Preview copy verification failed; do not deploy')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--title', required=True)
    parser.add_argument('--artist', required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    if not source.is_relative_to('/vault/shared/media/music') or source.suffix.lower() != '.mp3':
        parser.error('Select one MP3 from /vault/shared/media/music')
    print(stage_track(source, Path('/srv/appdata/docker/staging/blog/listening'), args.title, args.artist))
