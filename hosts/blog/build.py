#!/usr/bin/env python3
"""Native static blog builder. Content refreshes reuse code, dependencies and caches."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPOSITORY = 'git@github.com:rafael-alani/blog.git'


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def write(path, value):
    temporary = path.with_suffix('.next')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def import_content(source, workspace, mode):
    # Replacing the selected trees also removes deleted/unpublished articles and media.
    for directory in ('interests', 'obsidian'):
        target = workspace / 'content' / directory
        target.mkdir(parents=True, exist_ok=True)
        run('rsync', '-a', '--delete', '--chmod=D755,F644', str(source / mode / directory) + '/', str(target) + '/')
    (workspace / 'content/route-history.json').write_text((source / 'history.json').read_text())


def build(environment, refresh_code=False):
    config = read(HERE / 'environments.json')[environment]
    root = Path('/srv/appdata/docker') / environment / 'blog'
    cache = Path('/var/lib/dothomelab-blog')
    cache.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'native-build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        started = time.monotonic()
        current = read(root / 'current.json')
        commit = current.get('commit')
        mirror = cache / 'repository.git'
        if refresh_code or not commit or not mirror.exists():
            if not mirror.exists():
                run('git', 'init', '--quiet', '--bare', str(mirror))
            key = root / 'git/id_ed25519'
            ssh = shlex.join(['ssh', '-i', str(key), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                             '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(key.with_name('known_hosts'))])
            run('git', '-c', 'core.sshCommand=' + ssh, '--git-dir', str(mirror), 'fetch', '--quiet',
                REPOSITORY, '+refs/heads/' + config['branch'] + ':refs/heads/' + config['branch'])
            if refresh_code or not commit:
                commit = run('git', '--git-dir', str(mirror), 'rev-parse', 'refs/heads/' + config['branch'], capture_output=True).stdout.strip()
        content = read(root / 'editorial/current.json')
        if not content:
            print('Blog: waiting for the first editorial export', flush=True)
            return
        revision = content['revision']
        digest = hashlib.sha256(json.dumps([config, content.get('modes', {}).get(config['mode'], revision)]).encode()).hexdigest()
        if current.get('native') and current.get('commit') == commit and current.get('content_digest') == digest and (cache / 'site/current/client/index.html').exists():
            print(json.dumps({'environment': environment, 'unchanged': True}), flush=True)
            return
        workspace = cache / 'workspace'
        if read(cache / 'code.json').get('commit') != commit:
            code = cache / ('code-' + commit)
            code.mkdir(exist_ok=True)
            archive = cache / ('code-' + commit + '.tar')
            if not archive.exists():
                run('git', '--git-dir', str(mirror), 'archive', '--output=' + str(archive), commit)
            run('tar', '-xf', str(archive), '-C', str(code))
            workspace.mkdir(exist_ok=True)
            run('rsync', '-a', '--delete', '--exclude=node_modules/', '--exclude=.cache/', '--exclude=build/',
                str(code) + '/', str(workspace) + '/')
            workspace.chmod(0o700)
            write(cache / 'code.json', {'commit': commit})
        package_hash = hashlib.sha256((workspace / 'package-lock.json').read_bytes()).hexdigest()
        if read(cache / 'dependencies.json').get('digest') != package_hash or not (workspace / 'node_modules').is_dir():
            run('npm', 'ci', '--no-audit', '--no-fund', cwd=workspace)
            write(cache / 'dependencies.json', {'digest': package_hash})
        import_content(root / 'editorial' / revision, workspace, config['mode'])
        prepared = time.monotonic()
        site = cache / 'site'
        site.mkdir(exist_ok=True, mode=0o755)
        release = site / (str(time.time_ns()) + '-' + commit[:12])
        release.mkdir(mode=0o755)
        env = {**os.environ, 'CONTENT_PREVIEW': '1' if environment == 'staging' else '0',
               'PUBLIC_SITE_URL': config['origin'], 'PUBLIC_UMAMI_SCRIPT_URL': config['origin'] + '/telemetry/script.js',
               'PUBLIC_UMAMI_WEBSITE_ID': config['website_id'], 'ASTRO_TELEMETRY_DISABLED': '1',
               'STATIC_OUTPUT_DIR': str(release / 'client'), 'NODE_OPTIONS': '--dns-result-order=ipv4first'}
        stages = {}
        for name, command in (
            ('generate', ['npm', 'run', 'content:prepare']),
            ('astro', ['node_modules/.bin/astro', 'build']),
            ('finalize', ['node', '--import', 'tsx', 'scripts/finalize-static-build.ts']),
        ):
            stage = time.monotonic()
            run(*command, cwd=workspace, env=env)
            stages[name] = round(time.monotonic() - stage, 3)
        redirects = (workspace / 'build/redirects.conf').read_bytes()
        (release / 'redirects.conf').write_bytes(redirects)
        if not (release / 'client/index.html').exists():
            raise RuntimeError('Static build did not produce index.html')
        old_link = site / 'current'
        old_redirects = (old_link / 'redirects.conf').read_bytes() if old_link.exists() else None
        temporary = site / 'current.next'
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(release.name)
        temporary.replace(old_link)
        if subprocess.run(['systemctl', 'is-active', '--quiet', 'dothomelab-blog-web.service']).returncode == 0 and old_redirects != redirects:
            run('systemctl', 'reload', 'dothomelab-blog-web.service')
        state = {'native': True, 'commit': commit, 'branch': config['branch'], 'repository': 'https://github.com/rafael-alani/blog.git',
                 'content': revision, 'content_digest': digest, 'release': release.name, 'exportedAt': content.get('exportedAt'),
                 'activatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 'timings': {'prepare': round(prepared - started, 3), **stages, 'total': round(time.monotonic() - started, 3)}}
        write(root / 'previous.json', current)
        write(root / 'current.json', state)
        write(release / 'release.json', state)
        print(json.dumps({'environment': environment, **state}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', choices=['staging', 'production'], required=True)
    parser.add_argument('--refresh-code', action='store_true')
    args = parser.parse_args()
    os.umask(0o022)
    build(args.environment, args.refresh_code)
