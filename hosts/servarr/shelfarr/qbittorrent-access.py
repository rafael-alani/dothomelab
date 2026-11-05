#!/usr/bin/env python3
"""Check/reconcile only the private qBittorrent access policy, across INI layouts."""
import argparse
import ipaddress
import os
from pathlib import Path
import tempfile


def reconcile(text, subnet):
    network = ipaddress.ip_network(subnet, strict=True)
    if network.version != 4 or not network.is_private or network.prefixlen < 16:
        raise ValueError('Refusing unsafe qBittorrent bypass subnet')
    desired = {'AuthSubnetWhitelist': str(network),
               'AuthSubnetWhitelistEnabled': 'true', 'LocalHostAuth': 'true'}
    lines = text.splitlines()
    # qBittorrent 5.3 migrated Preferences/WebUI\ keys to a WebUI section.
    modern = '[WebUI]' in lines
    section_name = '[WebUI]' if modern else '[Preferences]'
    prefix = '' if modern else 'WebUI\\'
    if lines.count(section_name) != 1:
        raise ValueError('Missing or ambiguous qBittorrent access section')
    section = None
    found = set()
    result = []
    for line in lines:
        if line.startswith('[') and line.endswith(']'):
            section = line
        key = line.split('=', 1)[0]
        name = key.removeprefix(prefix)
        if section == section_name and key == prefix + name and name in desired:
            if name in found:
                raise ValueError('Duplicate qBittorrent access setting')
            found.add(name)
            line = key + '=' + desired[name]
        result.append(line)
    position = result.index(section_name) + 1
    for key in sorted(set(desired) - found):
        result.insert(position, prefix + key + '=' + desired[key])
        position += 1
    return '\n'.join(result) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subnet', required=True)
    parser.add_argument('--write', action='store_true', help='Only while qBittorrent is stopped')
    parser.add_argument('--config', type=Path, default=Path('/docker/qbittorrent/qBittorrent/qBittorrent.conf'))
    args = parser.parse_args()
    original = args.config.read_text()
    expected = reconcile(original, args.subnet)
    if original == expected:
        return 0
    if not args.write:
        print('qBittorrent internal access policy needs reconciliation')
        return 1
    metadata = args.config.stat()
    descriptor, temporary = tempfile.mkstemp(prefix='.qbit.', dir=args.config.parent)
    try:
        os.fchmod(descriptor, metadata.st_mode & 0o777)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
        os.chown(temporary, metadata.st_uid, metadata.st_gid)
        os.replace(temporary, args.config)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ValueError as error:
        raise SystemExit(str(error))
