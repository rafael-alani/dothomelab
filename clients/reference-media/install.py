#!/usr/bin/env python3
"""Install a committed, private awake-only desktop collector release."""
import argparse
import fcntl
import json
import os
import plistlib
import shutil
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vault', type=Path, required=True)
    p.add_argument('--host', required=True)
    p.add_argument('--instagram-saved-url', required=True)
    p.add_argument('--enable', action='store_true')
    a = p.parse_args()
    os.umask(0o077)
    source = Path(__file__).resolve().parent
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--', '.'], text=True)
    if dirty:
        raise SystemExit('Commit the collector before installing its release.')
    if not (a.vault / '.obsidian').is_dir() or a.vault.is_symlink():
        raise SystemExit('Use an existing local vault.')
    support = Path.home() / 'Library/Application Support/dothomelab-references'
    support.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not (support / 'ingest-key').exists():
        raise SystemExit('Enroll the scoped ingestion key first; see the runbook.')
    # Refuse to replace a running collector; release files and launchd change
    # together while the same nonblocking lock excludes scheduled starts.
    install_lock = (support / 'worker.lock').open('a')
    try:
        fcntl.flock(install_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Collector is busy; retry installation when this run finishes.')
    release = support / 'releases' / revision
    release.mkdir(parents=True, exist_ok=True)
    for file in source.glob('*.py'):
        shutil.copyfile(file, release / file.name)
    shutil.copyfile(source / 'requirements.txt', release / 'requirements.txt')
    (release / 'DEPLOYED_COMMIT').write_text(revision + '\n')
    python = support / 'venv/bin/python'
    if not python.exists():
        subprocess.run(['python3', '-m', 'venv', str(support / 'venv')], check=True)
    check = 'import importlib.metadata as m; import sys; from pathlib import Path; assert all(m.version(n)==v for n,v in (line.split("==") for line in Path(sys.argv[1]).read_text().splitlines() if line and not line.startswith("#")))'
    ready = subprocess.run([str(python), '-c', check, str(release / 'requirements.txt')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if ready.returncode:
        subprocess.run([str(python), '-m', 'ensurepip', '--upgrade'], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(release / 'requirements.txt')], check=True, stdout=subprocess.DEVNULL)
    config = support / 'config.json'
    if config.exists():
        shutil.copyfile(config, support / ('config.before-' + revision[:12] + '.json'))
    config.write_text(json.dumps({'host': a.host, 'vault': str(a.vault.resolve()), 'instagram_saved_url': a.instagram_saved_url}))
    plist = Path.home() / 'Library/LaunchAgents/media.rafael.reference-collector.plist'
    plist.parent.mkdir(parents=True, exist_ok=True)
    label = 'media.rafael.reference-collector'
    service = f'gui/{os.getuid()}/{label}'
    if plist.exists():
        shutil.copyfile(plist, support / ('agent.before-' + revision[:12] + '.plist'))
    subprocess.run(['launchctl', 'bootout', service], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with plist.open('wb') as file:
        plistlib.dump({'Label': label, 'ProgramArguments': [str(python), str(release / 'worker.py'), '--support', str(support)],
                      'StartInterval': 600, 'RunAtLoad': True, 'ProcessType': 'Background', 'LimitLoadToSessionType': 'Aqua',
                      'StandardOutPath': str(support / 'worker.log'), 'StandardErrorPath': str(support / 'worker.log')}, file)
    (support / 'DEPLOYED_COMMIT').write_text(revision + '\n')
    if a.enable:
        subprocess.run(['launchctl', 'enable', service], check=True)
        subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(plist)], check=True)
    print('Installed collector', revision, 'enabled' if a.enable else 'not started')


if __name__ == '__main__':
    main()
