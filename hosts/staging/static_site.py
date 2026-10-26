"""Publish a complete generated static tree while retaining the running web container."""
import os
from pathlib import Path


def activate(app_root: Path, release: Path, run):
    root = app_root / 'static-site'
    root.mkdir(exist_ok=True, mode=0o755)
    root.chmod(0o755)
    destination = root / release.name
    marker = destination / '.complete'
    if not marker.exists():
        if destination.exists():
            raise RuntimeError('Incomplete static tree retained; inspect before retrying')
        destination.mkdir(mode=0o755)
        destination.chmod(0o755)
        image = run('docker', 'compose', '--env-file', str(release / 'deploy.env'),
                    '-f', str(release / 'compose.yaml'), 'config', '--images', capture=True)
        if not image or '\n' in image:
            raise RuntimeError('Static publication requires one web image')
        container = run('docker', 'create', image, capture=True)
        try:
            run('docker', 'cp', container + ':/usr/share/nginx/html', str(destination / 'client'))
            run('docker', 'cp', container + ':/etc/nginx/redirects.conf', str(destination / 'redirects.conf'))
        finally:
            run('docker', 'rm', container)
        if not (destination / 'client/about/index.html').is_file():
            raise RuntimeError('Static artifact is incomplete')
        (destination / 'redirects.conf').chmod(0o644)
        marker.write_text(release.name)
    temporary = root / 'current.next'
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(release.name, target_is_directory=True)
    os.replace(temporary, root / 'current')
