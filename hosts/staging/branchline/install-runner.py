#!/usr/bin/env python3
"""CT114: pin the native runner to the accepted Branchline release and recipe."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = Path('/srv/appdata/docker/staging/branchline')
ARTIFACTS = Path('/srv/appdata/docker/staging/branchline-artifacts/labrador/artifacts')


def main():
    if os.geteuid() or os.uname().nodename != 'staging':
        raise RuntimeError('Run as root in CT114')
    subprocess.run(['bash', str(HERE / 'install-node.sh')], check=True)
    release = json.loads((ROOT / 'current.json').read_text())
    sha = release['commit']
    source = Path('/var/lib/dothomelab-staging/branchline') / sha
    if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != sha:
        raise RuntimeError('Runner source does not match the accepted web release')
    target = Path('/opt/branchline-runner/releases') / sha
    if not target.exists():
        temporary = target.with_name(sha + '.preparing-' + uuid4().hex[:8])
        shutil.copytree(source, temporary, ignore=shutil.ignore_patterns('.git', 'node_modules'))
        (temporary / 'DEPLOYED_COMMIT').write_text(sha + '\n')
        temporary.rename(target)
    if (target / 'DEPLOYED_COMMIT').read_text().strip() != sha or not (target / 'server/preview-runner.js').is_file():
        raise RuntimeError('Existing runner release is incomplete or has a different identity')
    recipe = HERE.parent / 'previews/labrador/prepare.py'
    revision = hashlib.sha256(recipe.read_bytes() + (ARTIFACTS / 'manifest.json').read_bytes()).hexdigest()
    recipe_dir = Path('/opt/branchline-recipes') / revision
    recipe_dir.mkdir(parents=True, exist_ok=True)
    installed = recipe_dir / 'prepare.py'
    if installed.exists() and installed.read_bytes() != recipe.read_bytes():
        raise RuntimeError('Immutable recipe changed')
    shutil.copyfile(recipe, installed)
    installed.chmod(0o755)
    config = {
        'socket': '/run/branchline-preview/runner.sock',
        'repository': str(ROOT / 'workspace/repository.git'),
        'stateDir': str(ROOT / 'preview-state'),
        'workDir': '/srv/appdata/docker/staging/previews',
        'portStart': 12000, 'portEnd': 12899,
        'allowedHostIP': '192.168.0.114',
        'limits': {'maxBuilds': 1, 'maxRunning': 3},
        'bounds': {'maxBuilds': 1, 'maxRunning': 3},
        'maxServices': 3, 'maxEnvironmentMemoryBytes': 4 * 1024**3,
        'recipe': {
            'revision': revision,
            'prepare': ['python3', str(installed)],
            'composeFiles': ['{source}/end_to_end/compose.yml', '{preview}/compose.override.yaml'],
            'envFile': '{preview}/runtime.env',
            'environment': {'LABRADOR_ARTIFACTS': str(ARTIFACTS), 'LABRADOR_BIND_IP': '192.168.0.114'},
            'allowedServices': ['database', 'skills', 'jaeger'],
            'allowedImages': ['branchline-skills:{id}', 'mysql:9.0.1', 'cr.jaegertracing.io/jaegertracing/jaeger:2.10.0'],
            'urlTemplate': 'https://bl-{port}.staging.rafael.media',
            'healthUrl': 'http://192.168.0.114:{port}/',
        },
    }
    # Pins captured by the recipe proof avoid silently changing builder toolchains.
    pins = ARTIFACTS.parent / 'builder-images.json'
    if pins.exists():
        config['recipe']['environment'].update(json.loads(pins.read_text()))
    os.umask(0o077)
    file = ROOT / 'runner.json'
    if file.exists():
        old = json.loads(file.read_text())
        config['bounds'] = old.get('bounds', config['bounds'])
        shutil.copyfile(file, ROOT / ('runner.before-' + sha[:12] + '.json'))
    temporary = file.with_suffix('.tmp')
    temporary.write_text(json.dumps(config, indent=2) + '\n')
    temporary.replace(file)
    current = target.parent.parent / 'current'
    link = current.with_name('current.next')
    if link.is_symlink():
        link.unlink()
    link.symlink_to(target)
    link.replace(current)
    for name in ['dothomelab-branchline-preview.service', 'dothomelab-branchline-gateway.service']:
        shutil.copyfile(HERE / name, Path('/etc/systemd/system') / name)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'dothomelab-branchline-preview.service', 'dothomelab-branchline-gateway.service'], check=True)
    subprocess.run(['systemctl', 'restart', 'dothomelab-branchline-preview.service', 'dothomelab-branchline-gateway.service'], check=True)
    print(f'Installed native preview runner {sha} and recipe {revision}')


if __name__ == '__main__':
    main()
