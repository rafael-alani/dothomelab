#!/usr/bin/env python3
"""Add CT114 to the existing freeze list without displaying backup secrets."""
import os
import re
from pathlib import Path

path = Path('/etc/dothomelab/pbs-appdata.conf')
text = path.read_text()
match = re.search(r'^QUIESCE_CTIDS="([0-9 ]*)"$', text, re.MULTILINE)
if not match:
    raise SystemExit('Expected a quoted numeric QUIESCE_CTIDS list')
ctids = match[1].split()
if '114' not in ctids:
    ctids.append('114')
    temporary = path.with_suffix('.staging.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text[:match.start()] + 'QUIESCE_CTIDS="' + ' '.join(ctids) + '"' + text[match.end():])
    temporary.replace(path)
print('CT114 is included in the appdata snapshot freeze list; no backup started')
