#!/usr/bin/env python3
"""Production blog code releases; content refreshes run automatically."""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent

def app():
    return json.loads((HERE / 'apps.json').read_text())['blog']


def dependencies():
    missing = []
    for name, url in app()['dependencies'].items():
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status != 200:
                    raise RuntimeError('Unhealthy dependency')
        except Exception:
            missing.append(name)
    if missing:
        raise RuntimeError('Unavailable production dependencies: ' + ', '.join(missing) +
                           '; notify Rafael, do not provision replacements or use demo mode')
    print('Production dependencies reachable: ' + ', '.join(app()['dependencies']))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--activate', action='store_true', help='Build the current origin/main with current published content')
    args = parser.parse_args()
    if args.check:
        dependencies()
    elif args.activate:
        subprocess.run(['python3', str(HERE.parent / 'blog/build.py'), '--environment', 'production', '--refresh-code'], check=True)
        subprocess.run(['systemctl', 'start', 'dothomelab-blog-web.service'], check=True)
    else:
        parser.error('Choose --check or --activate; content updates require neither')


if __name__ == '__main__':
    main()
