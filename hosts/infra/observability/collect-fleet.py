#!/usr/bin/env python3
"""PVE: export allowlisted Pulse resource measurements and state changes.

Reuse Pulse's existing PVE/Docker collection. No application logs, environment,
mounts, commands, tokens or arbitrary labels enter the monitoring stores.
"""
import datetime
import json
import math
import os
from pathlib import Path
import re
import runpy
import time

HERE = Path(__file__).resolve().parent
ROOT = Path('/srv/appdata/docker/observability/fleet')
GUESTS = {'servarr': '102', 'infra': '110', 'apps': '112',
          'proxmox-backup-server': '113', 'staging': '114', 'production': '115'}


def label(value):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', str(value))[:128]


def timestamp(value):
    try:
        return datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, OverflowError):
        return 0


def identity(row):
    kind = row['type']
    docker, pve = row.get('docker', {}), row.get('proxmox', {})
    if kind == 'agent' and not pve.get('nodeName'):
        return None
    guest = docker.get('hostname') or (row['name'] if kind in ('system-container', 'vm') else 'host')
    environment = 'staging' if guest == 'staging' else ('infra' if guest in ('infra', 'host') else 'production')
    labels = docker.get('labels', {})
    project = labels.get('dothomelab.project') or labels.get('com.docker.compose.project') or row['name']
    project = re.sub(r'^(staging|production)-', '', project)
    service = labels.get('com.docker.compose.service') or row['name']
    if project == 'blog' and service == 'web':
        service = 'blog'
    return {k: label(v) for k, v in dict(host='afa', guest=guest,
        guest_id=pve.get('vmid') or GUESTS.get(guest, 'host'), project=project,
        service_name=service, environment=environment, resource=row['name'],
        resource_type='node' if kind == 'agent' else kind).items()}


def render(rows, previous, now):
    lines, states, events = [], {}, []
    def metric(name, labels, value):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            return
        encoded = ','.join(f'{k}={json.dumps(str(v))}' for k, v in sorted(labels.items()))
        lines.append(f'homelab_{name}{{{encoded}}} {value}')
    for row in rows:
        labels = identity(row)
        if labels is None:
            continue
        key = json.dumps(labels, sort_keys=True)
        if key in states:
            raise ValueError('Duplicate fleet resource identity')
        observed = timestamp(row.get('lastSeen'))
        fresh = 0 <= now - observed < 180
        status = row.get('status')
        status = status if status in ('online', 'offline', 'warning', 'error', 'unknown') else 'unknown'
        docker = row.get('docker', {})
        if row['type'] == 'app-container':
            # Pulse can mark a discovered exited container online despite its runtime state.
            runtime = docker.get('containerState')
            if runtime != 'running':
                status = 'offline' if runtime in ('exited', 'dead', 'created', 'paused') else 'unknown'
            elif 0 < timestamp(docker.get('startedAt')) <= timestamp(docker.get('finishedAt')):
                # Conflicting Docker list/detail fields cannot establish current availability.
                status = 'unknown'
        health = docker.get('health') if status == 'online' else None
        health = health if health in ('healthy', 'unhealthy', 'starting') else 'unavailable'
        state = dict(status=status, health=health, fresh=fresh)
        states[key] = state
        metric('resource_observed_timestamp_seconds', labels, observed)
        metric('resource_fresh', labels, int(fresh))
        metric('resource_online', labels, int(status == 'online'))
        metric('resource_state_known', labels, int(status != 'unknown'))
        if health != 'unavailable':
            metric('resource_healthy', labels, int(health == 'healthy'))
        # Missing/stale measurements remain absent, never a reassuring zero.
        if fresh and status == 'online':
            metrics = row.get('metrics', {})
            for name in ('cpu', 'memory', 'disk'):
                value = metrics.get(name, {})
                if value.get('observation', {}).get('state', 'current') != 'current':
                    continue
                metric('resource_' + name + '_percent', labels, value.get('percent'))
                if name != 'cpu':
                    for field in ('used', 'total'):
                        metric(f'resource_{name}_{field}_bytes', labels, value.get(field))
            for source, name in [('netIn', 'network_receive'), ('netOut', 'network_transmit'),
                                 ('diskRead', 'disk_read'), ('diskWrite', 'disk_write')]:
                metric(f'resource_{name}_bytes_per_second', labels, metrics.get(source, {}).get('value'))
        if previous.get(key) != state:
            events.append({**labels, **state, 'event': 'resource_state',
                           'timestamp': datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat()})
    lines.append(f'homelab_fleet_collection_timestamp_seconds {now}')
    return '\n'.join(lines) + '\n', states, events


def main():
    helper = runpy.run_path(str(HERE.parent / 'pulse/configure-monitoring.py'))
    env = helper['load_env']()
    pulse = helper['Pulse'](env['PULSE_AUTH_USER'], env['PULSE_AUTH_PASS'])
    rows = []
    for kind in ('node', 'system-container', 'vm', 'app-container'):
        rows.extend(helper['resource_rows'](pulse, kind))
    if not rows:
        raise RuntimeError('Pulse returned no resources')
    state_path = ROOT / 'state.json'
    previous = json.loads(state_path.read_text()) if state_path.exists() else {}
    text, states, events = render(rows, previous, time.time())
    os.umask(0o027)
    # Files are small; bounded rotation retains the preceding event file.
    event_path = ROOT / 'events.jsonl'
    if event_path.exists() and event_path.stat().st_size > 5 * 1024 * 1024:
        event_path.replace(ROOT / 'events.previous.jsonl')
    with event_path.open('a') as stream:
        for event in events:
            stream.write(json.dumps(event, separators=(',', ':')) + '\n')
    event_path.chmod(0o644)
    for name, data, mode in [('fleet.prom', text, 0o644), ('state.json', json.dumps(states), 0o600)]:
        temporary = ROOT / (name + '.next')
        temporary.write_text(data)
        temporary.chmod(mode)
        temporary.replace(ROOT / name)
    print(f'Exported {len(states)} resource identities and {len(events)} state changes; secrets excluded')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(f'Fleet collection failed ({type(error).__name__}); previous data retained and freshness will expire') from None
