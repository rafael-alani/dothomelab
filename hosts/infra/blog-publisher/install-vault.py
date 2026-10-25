#!/usr/bin/env python3
"""Install non-destructive Obsidian authoring files on the operator machine."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import uuid

HERE = Path(__file__).resolve().parent


def install(vault: Path, blog_repo: Path):
    if not (vault / '.obsidian').is_dir() or not (blog_repo / 'content/interests').is_dir():
        raise ValueError('Pass an existing Obsidian vault and blog repository')
    created = []

    def create(relative, content):
        target = vault / relative
        if target.exists():
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x') as handle:
            handle.write(content)
        created.append(str(relative))

    settings_file = vault / '.obsidian/templates.json'
    settings = json.loads(settings_file.read_text()) if settings_file.exists() else {}
    template_folder = settings.get('folder') or '3. Resources/Templates'
    for source in (blog_repo / 'content/interests').glob('**/_index.md'):
        create(Path('Blog') / source.relative_to(blog_repo / 'content/interests'), source.read_text())
    article = (HERE / 'templates/Blog article.md').read_text()
    for kind in ('article', 'poem', 'project'):
        create(Path(template_folder) / f'Blog {kind}.md', article.replace('kind: article', f'kind: {kind}'))
    create(Path(template_folder) / 'Blog topic.md', (HERE / 'templates/Blog topic.md').read_text())
    for name in ('_Start here.md', 'Articles.base'):
        create(Path('Blog') / name, (HERE / 'templates' / name).read_text())
    source_note = "2. Areas/7. Entertainment/Songs/Mama's boy - Dominic Fike.md"
    if (vault / source_note).is_file():
        metadata = dict(id=str(uuid.uuid4()), title="Mama’s Boy — Dominic Fike",
                        description='Listening notes on Mama’s Boy by Dominic Fike.',
                        publishedAt=datetime.date.today().isoformat(), status='draft', kind='article',
                        **{'cover-media': '', 'cover-alt': '', 'tags': []})
        create(Path('Blog/art-corner/songs/mamas-boy-dominic-fike.md'),
               '---\n' + '\n'.join(f'{key}: {json.dumps(value, ensure_ascii=False)}' for key, value in metadata.items()) +
               f'\n---\n\n![[{source_note.removesuffix(".md")}]]\n')
    backup = vault / '.blog-publisher-backups' / datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    for file in (settings_file, vault / '.obsidian/core-plugins.json'):
        if file.exists():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, backup / file.name)
    settings['folder'] = template_folder
    settings_file.write_text(json.dumps(settings, indent=2) + '\n')
    plugins_file = vault / '.obsidian/core-plugins.json'
    plugins = json.loads(plugins_file.read_text())
    if isinstance(plugins, list):
        if 'templates' not in plugins:
            plugins.append('templates')
    else:
        plugins['templates'] = True
    plugins_file.write_text(json.dumps(plugins, indent=2) + '\n')
    (backup / 'created-files.json').write_text(json.dumps(created, indent=2) + '\n')
    print(json.dumps({'created': len(created), 'blog': str(vault / 'Blog'),
                      'templates': str(vault / template_folder), 'settings_backup': str(backup)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True)
    parser.add_argument('--blog-repo', type=Path, required=True)
    args = parser.parse_args()
    install(args.vault.resolve(), args.blog_repo.resolve())
