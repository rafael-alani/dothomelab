// One-time, additive migration: wrapper identities stay in Blog, never course notes.
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import path from 'node:path';
import matter from 'gray-matter';
const [vault, repo] = process.argv.slice(2);
if (!vault || !repo) throw new Error('Usage: node migrate-maps.mjs VAULT BLOG_REPOSITORY');
const configs = JSON.parse(await readFile(path.join(repo, 'content/obsidian/collections.json')));
const planned = [];
for (const config of configs) {
  await access(path.join(vault, config.entrypoint));
  const original = path.join(repo, 'content/interests', config.articleUrl + '.mdx');
  const { data } = matter(await readFile(original, 'utf8'));
  const target = path.join(vault, 'Blog', path.dirname(config.articleUrl), config.title.replaceAll('/', '-') + '.md');
  const content = matter.stringify(`![[${config.entrypoint.replace(/\.md$/, '')}]]\n`, {
    id: data.id, url: data.url, title: config.title, description: data.description,
    publishedAt: data.publishedAt, status: 'draft', kind: data.kind, tags: data.tags,
    'map-id': config.id,
  });
  try {
    const existing = await readFile(target, 'utf8');
    if (matter(existing).data.id !== data.id) throw new Error('Existing wrapper has a different identity');
    continue;
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  planned.push({ target, content });
}
const backup = path.join(vault, '.blog-publisher-backups', 'maps-' + new Date().toISOString().replaceAll(':', '-'));
await mkdir(backup, { recursive: true });
await writeFile(path.join(backup, 'created-files.json'), JSON.stringify(planned.map(p => path.relative(vault, p.target)), null, 2));
for (const { target, content } of planned) {
  await mkdir(path.dirname(target), { recursive: true });
  await writeFile(target, content, { flag: 'wx' });
}
console.log(JSON.stringify({ created: planned.length, backup }));
