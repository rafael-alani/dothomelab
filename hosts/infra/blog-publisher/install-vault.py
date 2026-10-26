#!/usr/bin/env python3
"""Install non-destructive Obsidian authoring files on the operator machine."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import uuid

HERE = Path(__file__).resolve().parent


def install(vault: Path, blog_repo: Path, refresh_authoring=False):
    if not (vault / '.obsidian').is_dir() or not (blog_repo / 'content/interests').is_dir():
        raise ValueError('Pass an existing Obsidian vault and blog repository')
    plugin = vault / '.obsidian/plugins/templater-obsidian'
    if not (plugin / 'manifest.json').is_file():
        raise ValueError('Install Templater from Obsidian Community plugins first')
    created, refreshed = [], []
    backup = vault / '.blog-publisher-backups' / datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
    backup.mkdir(parents=True)

    def preserve(target):
        if target.exists():
            destination = backup / target.relative_to(vault)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)

    def create(relative, content, authoring=False):
        target = vault / relative
        if target.exists():
            if authoring and refresh_authoring and target.read_text() != content:
                preserve(target)
                target.write_text(content)
                refreshed.append(str(relative))
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x') as handle:
            handle.write(content)
        created.append(str(relative))

    settings_file = plugin / 'data.json'
    settings = json.loads(settings_file.read_text()) if settings_file.exists() else {}
    template_folder = settings.get('templates_folder') or '3. Resources/Templates'
    if Path(template_folder).is_absolute() or '..' in Path(template_folder).parts:
        raise ValueError('Templater folder must be inside the vault')
    for source in (blog_repo / 'content/interests').glob('**/_index.md'):
        relative = source.relative_to(blog_repo / 'content/interests')
        content = source.read_text()
        if relative == Path('about/_index.md'):
            before, metadata, body = content.split('---', 2)
            create(Path('Blog/about/about.md'), body.strip() + '\n')
            content = before + '---' + metadata + '---\n\n![[about]]\n'
        create(Path('Blog') / relative, content)
    article = (HERE / 'templates/Blog article.md').read_text()
    for kind in ('article', 'poem', 'project'):
        create(Path(template_folder) / f'Blog {kind}.md', article.replace('kind: article', f'kind: {kind}'), True)
    create(Path(template_folder) / 'Blog topic.md', (HERE / 'templates/Blog topic.md').read_text(), True)
    for name in ('_Start here.md', 'Articles.base'):
        create(Path('Blog') / name, (HERE / 'templates' / name).read_text(), True)
    source_note = "2. Areas/7. Entertainment/Songs/Mama's boy - Dominic Fike.md"
    if (vault / source_note).is_file():
        metadata = dict(id=str(uuid.uuid4()), title="Mama’s Boy — Dominic Fike",
                        description='Listening notes on Mama’s Boy by Dominic Fike.',
                        publishedAt=datetime.date.today().isoformat(), status='draft', kind='article',
                        **{'cover-media': '', 'cover-alt': '', 'tags': []})
        create(Path('Blog/art-corner/songs/mamas-boy-dominic-fike.md'),
               '---\n' + '\n'.join(f'{key}: {json.dumps(value, ensure_ascii=False)}' for key, value in metadata.items()) +
               f'\n---\n\n![[{source_note.removesuffix(".md")}]]\n')
    preserve(settings_file)
    settings['templates_folder'] = template_folder
    settings_file.write_text(json.dumps(settings, indent=2) + '\n')
    plugins_file = vault / '.obsidian/community-plugins.json'
    preserve(plugins_file)
    plugins = json.loads(plugins_file.read_text())
    if 'templater-obsidian' not in plugins:
        plugins.append('templater-obsidian')
    plugins_file.write_text(json.dumps(plugins, indent=2) + '\n')
    (backup / 'created-files.json').write_text(json.dumps(created, indent=2) + '\n')
    (backup / 'refreshed-files.json').write_text(json.dumps(refreshed, indent=2) + '\n')
    print(json.dumps({'created': len(created), 'refreshed': len(refreshed), 'blog': str(vault / 'Blog'),
                      'templates': str(vault / template_folder), 'settings_backup': str(backup)}))


def seed_about(vault: Path, blog_repo: Path):
    """Migrate the original empty About authoring files without replacing prose."""
    import re
    index = vault / 'Blog/about/_index.md'
    note = vault / 'Blog/about/about.md'
    source = (blog_repo / 'content/interests/about/_index.md').read_text()
    body = source.split('---', 2)[2].strip()
    existing_index = index.read_text()
    if existing_index.split('---', 2)[2].strip():
        raise ValueError('About index already has content; preserve it and migrate manually')
    existing_note = note.read_text() if note.exists() else ''
    if re.sub(r'%% Begin Waypoint %%.*?%% End Waypoint %%', '', existing_note, flags=re.S).strip():
        raise ValueError('About note already has content; preserve it and migrate manually')
    backup = vault / '.blog-publisher-backups' / ('about-' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    backup.mkdir(parents=True)
    shutil.copy2(index, backup / '_index.md')
    if note.exists():
        shutil.copy2(note, backup / 'about.md')
    note.write_text(body + '\n')
    index.write_text(existing_index.rstrip() + '\n\n![[about]]\n')
    print(json.dumps({'about': str(note), 'backup': str(backup)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True)
    parser.add_argument('--blog-repo', type=Path, required=True)
    parser.add_argument('--refresh-authoring', action='store_true',
                        help='Back up and replace the four Blog templates, guide and Articles base; never article notes')
    parser.add_argument('--seed-about', action='store_true', help='Back up and populate only the original empty About notes')
    args = parser.parse_args()
    if args.seed_about:
        seed_about(args.vault.resolve(), args.blog_repo.resolve())
    else:
        install(args.vault.resolve(), args.blog_repo.resolve(), args.refresh_authoring)
