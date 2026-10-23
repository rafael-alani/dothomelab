#!/usr/bin/env python3
"""CT112 acceptance: reads services; emits one harmless missing-path log probe."""
import base64
import json
import runpy
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
helper = runpy.run_path(str(HERE / 'initialize-umami.py'))


def get(url, authorization=None):
    headers = {'Authorization': authorization} if authorization else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def query(expression):
    result = get('http://192.168.0.112:9090/api/v1/query?' +
                 urllib.parse.urlencode({'query': expression}))
    assert result['status'] == 'success'
    return result['data']['result']


def main():
    env = dict(helper['parse'](helper['ENV']))
    token = helper['login'](env['BLOG_UMAMI_ADMIN_PASSWORD'])
    site = json.loads((HERE / 'website.json').read_text())
    actual = helper['api']('/api/websites/' + site['id'], token=token)
    assert all(actual[key] == value for key, value in site.items())
    end = int(time.time() * 1000)
    metrics = helper['api']('/api/websites/' + site['id'] + '/metrics/expanded?' + urllib.parse.urlencode({
        'startAt': end - 86400000, 'endAt': end, 'type': 'path'}), token=token)
    print('Umami stored pages (last 24 hours): ' + json.dumps([
        {'path': row['name'], 'pageviews': int(row['pageviews']), 'visitors': row['visitors']}
        for row in metrics]))

    auth = 'Basic ' + base64.b64encode(('admin:' + env['BLOG_GRAFANA_ADMIN_PASSWORD']).encode()).decode()
    dashboard = get('http://192.168.0.112:8091/api/dashboards/uid/blog', auth)
    assert dashboard['dashboard']['uid'] == 'blog'
    for uid in ('homelab-prometheus', 'homelab-loki'):
        health = get(f'http://192.168.0.112:8091/api/datasources/uid/{uid}/health', auth)
        assert health['status'] == 'OK', f'Grafana datasource {uid} failed'
    print('Grafana Blog dashboard and both datasource health checks passed')

    probes = query('probe_success{job=~"blog-https|blog-origin"}')
    assert {row['metric']['page'] for row in probes} == {'home', 'about', 'article', 'feed', 'origin'}
    assert all(row['value'][1] == '1' for row in probes), 'One or more endpoint probes failed'
    scrapes = query('up{job=~"blog-https|blog-origin|blog-blackbox|blog-alloy"}')
    assert len(scrapes) == 7 and all(row['value'][1] == '1' for row in scrapes)
    rules = get('http://192.168.0.112:9090/api/v1/rules')['data']['groups']
    blog_rules = next(group['rules'] for group in rules if group['name'] == 'blog')
    assert len(blog_rules) == 5 and all(rule['health'] == 'ok' for rule in blog_rules)
    print('Five content/status/TLS probes, seven monitoring scrapes and five alert-rule evaluations passed')

    path = '/__observability-verification-' + str(time.time_ns())
    before = time.time_ns()
    try:
        urllib.request.urlopen('https://blog.staging.rafael.media' + path + '?discard_me=verification', timeout=20)
        raise AssertionError('Missing path incorrectly returned success')
    except urllib.error.HTTPError as error:
        assert error.code == 404
    logql = '{service_name="blog",environment="staging"} | json | path="' + path + '"'
    for _ in range(30):
        result = get('http://192.168.0.112:3100/loki/api/v1/query_range?' + urllib.parse.urlencode({
            'query': logql, 'start': before - 1000000000, 'end': time.time_ns(), 'limit': 10}))
        rows = result['data']['result']
        if rows:
            entry = json.loads(rows[0]['values'][0][1])
            assert set(entry) == {'timestamp', 'method', 'path', 'status', 'bytes', 'request_time', 'synthetic'}
            assert entry['path'] == path and entry['status'] == 404
            assert 'discard_me' not in json.dumps(entry)
            print('Unique HTTPS404 request reached Loki with path preserved, query stripped and only allowed fields')
            break
        time.sleep(1)
    else:
        raise AssertionError('Unique log probe was not ingested within30 seconds')
    print('Notification delivery, external-WAN monitoring and browser analytics are separate acceptance checks')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(f'Blog verification failed ({type(error).__name__}); no credential-bearing response dumped') from None
