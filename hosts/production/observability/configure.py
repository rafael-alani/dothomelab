#!/usr/bin/env python3
"""CT110: isolate production analytics, dashboards and file-discovered probes."""
import argparse
import base64
import json
from pathlib import Path
import runpy
import shutil
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
STATE = Path('/srv/appdata/docker/production-monitoring')
helper = runpy.run_path(str(HERE.parents[1] / 'infra/observability/initialize-umami.py'))


def targets(active):
    labels = {'project': 'blog', 'environment': 'production', 'service_name': 'blog', 'host': 'afa', 'guest': 'production', 'guest_id': '115'}
    result = {key: [] for key in ('blackbox', 'alloy', 'https', 'origin')}
    if active:
        for key, port in [('blackbox', 9115), ('alloy', 12345)]:
            result[key] = [{'targets': [f'192.168.0.{110 if key == "blackbox" else 115}:{port}'], 'labels': labels}]
        for page, path, module in [('home', '/', 'blog_home_https'), ('about', '/about', 'blog_about_https'),
                                  ('article', '/technical-write-ups/ai/machine-and-deep-learning', 'blog_article_https'),
                                  ('feed', '/feed.xml', 'blog_feed_https')]:
            result['https'].append({'targets': ['https://rafael.ink' + path], 'labels': {**labels, 'page': page, 'module': 'production_' + module}})
        result['origin'] = [{'targets': ['http://192.168.0.115:8084/'],
                             'labels': {**labels, 'page': 'origin', 'module': 'production_blog_home_origin'}}]
    return result


def initialize_files():
    STATE.mkdir(mode=0o755, exist_ok=True)
    shutil.copyfile(HERE / 'alerts.yml', STATE / 'alerts.yml')
    for name, value in targets(False).items():
        path = STATE / (name + '.json')
        if not path.exists():
            path.write_text(json.dumps(value) + '\n')
            path.chmod(0o644)
    (STATE / 'alerts.yml').chmod(0o644)


def dashboard():
    source = HERE.parents[1] / 'infra/observability/grafana/dashboards/blog.json'
    text = source.read_text()
    for old, new in {
        'blog-https': 'blog-production-https', 'blog-origin': 'blog-production-origin',
        'blog-blackbox': 'blog-production-blackbox', 'blog-alloy': 'blog-production-alloy',
        'CT114': 'CT115', 'private HTTPS': 'public HTTPS', 'Private HTTPS': 'Public HTTPS',
        'blog.staging.rafael.media': 'rafael.ink',
        'a3417da8-b984-49df-9e5b-88ecb9b2f6da': '88d95afd-ff71-4f64-93ea-e57310dd952b',
    }.items():
        text = text.replace(old, new)
    value = json.loads(text)
    value.update(uid='blog-production', title='Blog — production', id=None, tags=['blog', 'production'])
    for panel in value['panels']:
        for target in panel.get('targets', []):
            target['expr'] = target['expr'].replace('environment="staging"', 'environment="production"').replace(
                'alertname=~"Blog.*"', 'alertname=~"ProductionBlog.*",environment="production"')
    value['templating']['list'][0]['current'] = {'text': 'production', 'value': 'production'}
    value['links'][0]['title'] = 'Umami — select The Night Archive — production'
    return value


def accounts():
    env = dict(helper['parse'](helper['ENV']))
    token = helper['login'](env['BLOG_UMAMI_ADMIN_PASSWORD'])
    site = json.loads((HERE / 'website.json').read_text())
    try:
        actual = helper['api']('/api/websites/' + site['id'], token=token)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        actual = None
    if actual is None:
        actual = helper['api']('/api/websites', site, token)
    if any(actual.get(key) != value for key, value in site.items()):
        raise RuntimeError('Production Umami identity conflict')
    auth = 'Basic ' + base64.b64encode(('admin:' + env['BLOG_GRAFANA_ADMIN_PASSWORD']).encode()).decode()
    production_dashboard = dashboard()
    # Retain the existing production bookmark alongside the shared environment dropdown.
    request = urllib.request.Request('http://192.168.0.110:8091/api/dashboards/db',
        data=json.dumps({'dashboard': production_dashboard, 'overwrite': True, 'message': 'Production scaffold'}).encode(),
        headers={'Authorization': auth, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if json.load(response).get('status') != 'success':
            raise RuntimeError('Production dashboard creation failed')
    print('Separate production Umami website and Grafana dashboard configured')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate-targets', action='store_true')
    parser.add_argument('--files-only', action='store_true')
    args = parser.parse_args()
    initialize_files()
    if args.activate_targets:
        for name, value in targets(True).items():
            path = STATE / (name + '.json')
            temporary = path.with_suffix('.next')
            temporary.write_text(json.dumps(value) + '\n')
            temporary.chmod(0o644)
            temporary.replace(path)
        print('Production probe targets enabled; delivery/alerts still need verification')
    elif not args.files_only:
        accounts()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(f'Production monitoring configuration failed ({type(error).__name__}); inspect privately') from None
