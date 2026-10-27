#!/usr/bin/env python3
"""Generate the shared fleet dashboard; JSON remains reviewable and provisioned."""
import json
from pathlib import Path

HERE = Path(__file__).parent
PROM = {'type': 'prometheus', 'uid': 'homelab-prometheus'}
LOKI = {'type': 'loki', 'uid': 'homelab-loki'}
SELECT = 'project=~"$project",environment=~"$environment",guest=~"$guest",service_name=~"$service"'


def variable(name, label, field, selector=''):
    query = f'label_values(homelab_resource_online{selector}, {field})'
    return dict(name=name, label=label, type='query', datasource=PROM,
                query={'query': query, 'refId': name}, definition=query,
                refresh=2, sort=1, multi=True, includeAll=True, allValue='.*',
                current={'text': ['All'], 'value': ['$__all']}, options=[])


def dashboard():
    variables = [variable('project', 'Project', 'project'),
        variable('environment', 'Environment', 'environment', '{project=~"$project"}'),
        variable('guest', 'Guest', 'guest', '{project=~"$project",environment=~"$environment"}'),
        variable('service', 'Service', 'service_name', '{project=~"$project",environment=~"$environment",guest=~"$guest"}')]
    panels = []
    def panel(title, expr, kind='timeseries', unit='short', datasource=PROM, width=12):
        number = len(panels)
        panels.append(dict(id=number+1, title=title, type=kind, datasource=datasource,
            gridPos={'x': 0 if number % 2 == 0 else 12, 'y': (number // 2)*8, 'w': width, 'h': 8},
            targets=[{'refId':'A', 'expr':expr, 'legendFormat':'{{guest}} / {{resource}}',
                      'datasource':datasource, 'instant':kind in ('stat','table')}],
            fieldConfig={'defaults':{'unit':unit},'overrides':[]},
            options={'legend':{'displayMode':'list','placement':'bottom'}}))
    panel('Resources reported online — check freshness alongside this', f'sum(homelab_resource_online{{{SELECT}}})', 'stat')
    panel('Resources with fresh observations', f'sum(homelab_resource_fresh{{{SELECT}}})', 'stat')
    panel('CPU usage reported by Pulse', f'homelab_resource_cpu_percent{{{SELECT}}}', unit='percent')
    panel('Memory used', f'homelab_resource_memory_used_bytes{{{SELECT}}}', unit='bytes')
    panel('Memory usage', f'homelab_resource_memory_percent{{{SELECT}}}', unit='percent')
    panel('Disk usage — where reported', f'homelab_resource_disk_percent{{{SELECT}}}', unit='percent')
    panel('Endpoint checks — reachability, not authenticated workflows', f'probe_success{{{SELECT}}}')
    panel('Endpoint duration', f'probe_duration_seconds{{{SELECT}}}', unit='s')
    panel('Latest observation age', f'time() - homelab_resource_observed_timestamp_seconds{{{SELECT}}}', unit='s')
    panel('Container health — absent when no health check exists', f'homelab_resource_healthy{{{SELECT}}}')
    panel('State changes and available access logs', '{'+SELECT+'}', 'logs', datasource=LOKI, width=24)
    panels[-1]['gridPos']['x'] = 0
    return dict(uid='homelab', title='Homelab', id=None, schemaVersion=41, version=1,
        tags=['homelab'], timezone='browser', editable=False, refresh='1m',
        description='One shared platform. Select project, environment, guest and service. Pulse supplies cached resource metrics; Loki contains resource state changes and declared sanitized application logs. No notification receiver is configured.',
        time={'from':'now-6h','to':'now'}, templating={'list':variables}, panels=panels,
        links=[{'title':'Website readership (Umami)','url':'https://analytics.rafael.media','type':'link','targetBlank':True},
               {'title':'Blog HTTP details','url':'/d/blog/blog','type':'link'}])


if __name__ == '__main__':
    (HERE / 'grafana/dashboards/homelab.json').write_text(json.dumps(dashboard(), indent=2)+'\n')
