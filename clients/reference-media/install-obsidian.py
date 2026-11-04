#!/usr/bin/env python3
"""Install only the Reference Boards integration; retain replaced files outside sync."""
import argparse
import datetime
import json
import shutil
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vault', type=Path, required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--pilot-asset', help='Immutable pilot basename, excluding .mp4')
    a = p.parse_args()
    assert a.vault.is_dir() and (a.vault / '.obsidian').is_dir()
    assert a.archive.is_absolute()
    source = Path(__file__).resolve().parent / 'obsidian'
    target = a.vault / '.obsidian/plugins/reference-boards'
    assert not target.is_symlink()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    support = Path.home() / 'Library/Application Support/dothomelab-references'
    if target.exists():
        rollback = support / 'rollback' / stamp / 'reference-boards'
        shutil.copytree(target, rollback)
        print('Previous plugin retained:', rollback)
    target.mkdir(parents=True, exist_ok=True)
    for name in ('manifest.json', 'styles.css'):
        shutil.copyfile(source / name, target / name)
    # Obsidian evaluates main.js with its own require; relative requires do not
    # resolve against the plugin directory. Bundle the small pure model inline.
    bundle = (source / 'main.js').read_text()
    for name in ('model', 'context'):
        inline = '(function () { const module = {exports: {}};\n' + (source / (name + '.cjs')).read_text() + '\nreturn module.exports; })()'
        bundle = bundle.replace("require('./" + name + ".cjs')", inline)
    (target / 'main.js').write_text(bundle)
    settings = target / 'data.json'
    data = json.loads(settings.read_text()) if settings.exists() else {}
    data['archiveRoot'] = str(a.archive)
    data['connectionFile'] = str(support / 'config.json')
    settings.write_text(json.dumps(data, indent=2) + '\n')
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    (target / 'DEPLOYED_COMMIT').write_text(revision + '\n')
    if a.pilot_asset:
        import re
        assert re.fullmatch('[a-f0-9]{64}', a.pilot_asset)
        catalog = a.vault / 'References/Catalog.json'
        if not catalog.exists():
            catalog.parent.mkdir(parents=True, exist_ok=True)
            catalog.write_text(json.dumps({'schema': 1, 'assets': [{
                'id': a.pilot_asset, 'path': f'objects/{a.pilot_asset}.mp4',
                'title': 'Board calibration — 24 seconds', 'collections': ['Acceptance example'],
                'source_url': None, 'attribution': 'Generated calibration pattern, not a source-account import',
            }], 'sources': {'instagram': 'not configured', 'yaay': 'not configured'}}, indent=2) + '\n')
    print('Installed Reference Boards. Enable it in Obsidian Community plugins.', revision)


if __name__ == '__main__':
    main()
