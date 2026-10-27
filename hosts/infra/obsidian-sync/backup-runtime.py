#!/usr/bin/env python3
"""Keep the verified Proton runtime independent of guest repository archives."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

RUNTIME = Path('/usr/local/lib/dothomelab-proton-backup')
MINIMUM_VERSION = 5
FILES = ('backup-runner.sh', 'backup-runtime.py', 'compose.yaml',
         'Dockerfile.proton', 'proton-entrypoint.sh', 'proton-backup.sh',
         'source-verification.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        # Compose diagnostics can contain configuration values.
        raise ValueError(f'{args[0]} check failed (exit {result.returncode})')
    return result.stdout.strip()


def candidate(project, minimum=MINIMUM_VERSION):
    images = re.findall(r'^\s+image: (dothomelab/proton-drive-cli:[^\s]+-backup-v([0-9]+))\s*$',
                        (project / 'compose.yaml').read_text(), re.MULTILINE)
    if len(images) != 1 or int(images[0][1]) < minimum:
        raise ValueError(f'Proton candidate must select backup-v{minimum} or later')
    helper = (project / 'proton-backup.sh').read_text()
    for required in ('source_verification inventory', 'source_verification verify',
                     'source_verification check', 'SOURCE-VERIFIED.json'):
        if required not in helper:
            raise ValueError('Proton candidate is missing required source verification')
    if not (project / 'source-verification.py').is_file():
        raise ValueError('Proton candidate has no source verifier')
    return images[0][0], int(images[0][1])


def check_repo(repo, runtime=RUNTIME):
    minimum = MINIMUM_VERSION
    receipt = runtime / 'current' / 'RELEASE.json'
    if receipt.exists():
        minimum = max(minimum, json.loads(receipt.read_text())['backup_version'])
    candidate(repo / 'hosts/infra/obsidian-sync', minimum)


def check_release(release):
    receipt = json.loads((release / 'RELEASE.json').read_text())
    if receipt['backup_version'] < MINIMUM_VERSION or set(receipt['files']) != set(FILES):
        raise ValueError('Installed Proton release is incomplete or too old')
    for name, expected in receipt['files'].items():
        if digest(release / name) != expected:
            raise ValueError(f'Installed Proton runtime file changed: {name}')
    image_id = receipt['image_id']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
        raise ValueError('Invalid installed image ID')
    if run('docker', 'image', 'inspect', '--format', '{{.Id}}', image_id) != image_id:
        raise ValueError('Pinned Proton image is unavailable')
    run('docker', 'compose', '--env-file', '/dev/null', '-f',
        str(release / 'compose.yaml'), '--profile', 'proton', 'config', '--quiet')
    return receipt


def pinned_compose(project, image, image_id):
    content = (project / 'compose.yaml').read_text()
    build = '    build:\n      context: .\n      dockerfile: Dockerfile.proton\n'
    if content.count(build) != 1:
        raise ValueError('Unrecognized Proton build configuration')
    return content.replace(build, '').replace('image: ' + image,
                                             'image: ' + image_id + '\n    pull_policy: never')


def install(project, revision, runtime=RUNTIME,
            runner=Path('/usr/local/sbin/dothomelab-proton-backup-runner')):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Install from a committed guest archive with DEPLOYED_COMMIT')
    check_repo(project.parents[2], runtime)
    image, version = candidate(project)
    image_id = run('docker', 'image', 'inspect', '--format', '{{.Id}}', image)
    image_files = {'proton-backup.sh': 'proton-backup',
                   'proton-entrypoint.sh': 'proton-entrypoint',
                   'source-verification.py': 'source-verification.py'}
    output = run('docker', 'run', '--rm', '--network', 'none', '--read-only',
                 '--entrypoint', 'sha256sum', image_id,
                 *('/usr/local/bin/' + name for name in image_files.values()))
    actual = {Path(line.split()[1]).name: line.split()[0] for line in output.splitlines()}
    if any(actual.get(target) != digest(project / name) for name, target in image_files.items()):
        raise ValueError('Built Proton image does not match the committed helper sources')
    runtime.mkdir(parents=True, exist_ok=True, mode=0o755)
    releases = runtime / 'releases'
    releases.mkdir(exist_ok=True)
    release = releases / revision
    if release.exists():
        receipt = check_release(release)
        if receipt['revision'] != revision or receipt['image_id'] != image_id:
            raise ValueError('Existing immutable release differs from this installation')
        for name in FILES:
            content = (project / name).read_bytes()
            if name == 'compose.yaml':
                content = pinned_compose(project, image, image_id).encode()
            if content != (release / name).read_bytes():
                raise ValueError('Existing release differs from the candidate files')
    else:
        with tempfile.TemporaryDirectory(prefix='.install-', dir=releases) as temporary:
            staged = Path(temporary) / 'release'
            staged.mkdir(mode=0o755)
            for name in FILES:
                shutil.copyfile(project / name, staged / name)
                (staged / name).chmod(0o755 if name.endswith('.sh') else 0o644)
            compose = staged / 'compose.yaml'
            compose.write_text(pinned_compose(project, image, image_id))
            receipt = {'revision': revision, 'backup_version': version, 'image_id': image_id,
                       'files': {name: digest(staged / name) for name in FILES}}
            (staged / 'RELEASE.json').write_text(json.dumps(receipt, indent=2) + '\n')
            check_release(staged)
            staged.rename(release)
    # Atomic links preserve every previous release for rollback.
    for destination, target in ((runtime / 'current', release),
                                (runner, runtime / 'current' / 'backup-runner.sh')):
        temporary = destination.with_name(destination.name + '.next')
        if temporary.exists() or temporary.is_symlink():
            raise ValueError('A pending runtime link requires inspection')
        temporary.symlink_to(target)
        temporary.replace(destination)
    return check_release(release)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('install', 'check', 'check-repo'))
    parser.add_argument('repo', nargs='?', type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parent
    try:
        if args.command == 'check-repo':
            if args.repo is None:
                parser.error('check-repo requires a repository path')
            check_repo(args.repo)
            print('Proton repository guard passed')
        else:
            if args.command == 'install':
                revision = (project.parents[2] / 'DEPLOYED_COMMIT').read_text().strip()
                receipt = install(project, revision)
            else:
                receipt = check_release(project)
            print(json.dumps({key: receipt[key] for key in ('revision', 'backup_version', 'image_id')}))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Proton runtime refused operation: {error}\n')


if __name__ == '__main__':
    main()
