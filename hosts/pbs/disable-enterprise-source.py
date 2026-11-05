#!/usr/bin/env python3
"""Disable PBS's subscription-only source; retain it for an explicit subscription change."""
from pathlib import Path
import re


def disable(text):
    # Refuse a mixed source file rather than disabling an unrelated repository.
    fields = dict(re.findall(r'^([A-Za-z-]+):\s*(.*)$', text, re.MULTILINE))
    if fields.get('URIs') != 'https://enterprise.proxmox.com/debian/pbs':
        raise ValueError('Unexpected PBS enterprise source URI')
    if fields.get('Components') != 'pbs-enterprise' or len(re.findall(r'^Types:', text, re.MULTILINE)) != 1:
        raise ValueError('Unexpected PBS enterprise source structure')
    if 'Enabled' in fields:
        return re.sub(r'^Enabled:.*$', 'Enabled: no', text, flags=re.MULTILINE)
    return text.rstrip() + '\nEnabled: no\n'


if __name__ == '__main__':
    path = Path('/etc/apt/sources.list.d/pbs-enterprise.sources')
    if path.exists():
        before = path.read_text()
        after = disable(before)
        if before != after:
            backup = path.with_suffix('.sources.before-dothomelab')
            if not backup.exists():
                backup.write_text(before)
            path.write_text(after)
        print('PBS enterprise source disabled; non-subscription source retained')
