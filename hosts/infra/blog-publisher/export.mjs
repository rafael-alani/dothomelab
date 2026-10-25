import { createHash } from 'node:crypto';
import { readFile, readdir, realpath, lstat, mkdir, writeFile, rename } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import matter from 'gray-matter';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkStringify from 'remark-stringify';
import wikiLink from '@flowershow/remark-wiki-link';
import sharp from 'sharp';

const parser = unified().use(remarkParse).use(remarkGfm).use(wikiLink);
const writer = unified().use(remarkStringify, { bullet: '-', unsafe: [
  { character: '{', inConstruct: ['phrasing'] },
  { character: '}', inConstruct: ['phrasing'] },
] }).use(remarkGfm);
const images = /\.(?:jpe?g|png|webp|avif|tiff?|gif|svg)$/i;
const media = /\.(?:jpe?g|png|webp|avif|tiff?|gif|svg|mp4|webm|pdf)$/i;
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const slug = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const text = node => node.value ?? node.children?.map(text).join('') ?? '';
const date = value => {
  const result = value instanceof Date ? value.toISOString().slice(0, 10) : value;
  if (typeof result !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(result) ||
      Number.isNaN(Date.parse(result)) || new Date(result).toISOString().slice(0, 10) !== result)
    throw new Error('Article dates must be real calendar dates in YYYY-MM-DD form');
  return result;
};
const uuid = key => {
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(key)) return key;
  const h = hash('dothomelab-blog:' + key);
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-5${h.slice(13, 16)}-a${h.slice(17, 20)}-${h.slice(20, 32)}`;
};

// Embedded YAML is discarded without parsing, including invalid YAML and private keys.
export function bodyOnly(source) {
  source = source.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
  if (!/^---[ \t]*\n/.test(source)) return source;
  const end = /^---[ \t]*$|^\.\.\.[ \t]*$/gm;
  end.lastIndex = source.indexOf('\n') + 1;
  const match = end.exec(source);
  if (!match) throw new Error('Embedded note has unterminated YAML frontmatter');
  return source.slice(match.index + match[0].length).replace(/^\n/, '');
}

function section(nodes, fragment) {
  if (!fragment) return nodes;
  if (fragment.startsWith('^')) throw new Error('Block embeds are not supported; use a heading embed');
  const start = nodes.findIndex(n => n.type === 'heading' && text(n).toLowerCase() === fragment.toLowerCase());
  if (start < 0) throw new Error(`Missing embedded heading: ${fragment}`);
  let end = start + 1;
  while (end < nodes.length && !(nodes[end].type === 'heading' && nodes[end].depth <= nodes[start].depth)) end++;
  return nodes.slice(start, end);
}

function codeRanges(source) {
  const protectedRanges = [];
  const collect = node => {
    if (node.type === 'code' || node.type === 'inlineCode') protectedRanges.push([node.position.start.offset, node.position.end.offset]);
    else node.children?.forEach(collect);
  };
  collect(parser.parse(source));
  return protectedRanges;
}
function parseBody(source) {
  const protectedRanges = codeRanges(source);
  const markers = [...source.matchAll(/%%/g)].map(m => m.index)
    .filter(offset => !protectedRanges.some(([start, end]) => offset >= start && offset < end));
  if (markers.length % 2) throw new Error('Unterminated Obsidian comment');
  for (let i = markers.length - 2; i >= 0; i -= 2) source = source.slice(0, markers[i]) + source.slice(markers[i + 1] + 2);
  return parser.parse(source);
}
function serializeBody(children) {
  const source = writer.stringify({ type: 'root', children });
  const ranges = codeRanges(source);
  // MDX recognizes ESM statements even in .md files. Keep note prose inert.
  return source.replace(/^(\s*)(import|export)(?=[ \t])/gm, (match, space, keyword, offset) =>
    ranges.some(([start, end]) => offset >= start && offset < end) ? match :
      `${space}&#${keyword.charCodeAt(0)};${keyword.slice(1)}`);
}

async function jsonOr(file, fallback) {
  try { return JSON.parse(await readFile(file, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return fallback; throw error; }
}
async function atomic(file, value) {
  await writeFile(file + '.tmp', JSON.stringify(value, null, 2) + '\n', { mode: 0o600 });
  await rename(file + '.tmp', file);
}

export async function exportVault({ vault, output, blog = 'Blog', quietMs = 10000 }) {
  vault = await realpath(vault);
  const files = [];
  async function scan(dir = '') {
    for (const item of await readdir(path.join(vault, dir), { withFileTypes: true })) {
      if (item.name.startsWith('.')) continue;
      const name = path.posix.join(dir, item.name);
      if (item.isSymbolicLink()) continue;
      if (item.isDirectory()) await scan(name);
      else if (item.isFile()) files.push(name);
    }
  }
  await scan();
  const inputs = new Map();
  async function read(name) {
    const file = path.resolve(vault, name);
    const actual = await realpath(file);
    if (!actual.startsWith(vault + path.sep) || actual !== file || name.split('/').some(p => p.startsWith('.')))
      throw new Error('Reference escapes the vault or uses a symlink/hidden path');
    if (name.includes('.sync-conflict-')) throw new Error('Resolve the referenced Syncthing conflict first');
    const conflicts = files.some(other => other.includes('.sync-conflict-') &&
      other.replace(/\.sync-conflict-[^.]+(?=\.[^.]+$)/, '') === name);
    if (conflicts) throw new Error('Resolve the referenced Syncthing conflict first');
    const stat = await lstat(file);
    if (!stat.isFile() || (quietMs > 0 && Date.now() - stat.mtimeMs < quietMs)) throw new Error('Referenced files are still changing; retry after sync settles');
    const bytes = await readFile(file);
    inputs.set(name, hash(bytes));
    return bytes;
  }
  function resolve(reference, from, note = false) {
    reference = decodeURIComponent(reference).replace(/^!?(?:\[\[)([\s\S]*?)\]\]$/, '$1').split('|')[0].trim();
    const [target, fragment = ''] = reference.split('#', 2);
    if (!target) return { name: from, fragment };
    if (/^(?:[a-z][a-z\d+.-]*:|\/\/|\/)/i.test(target)) throw new Error('Use a vault-relative local reference');
    const variants = note && !path.extname(target) ? [target, target + '.md'] : [target];
    const candidates = [...new Set(variants.flatMap(v => [path.posix.normalize(v), path.posix.join(path.posix.dirname(from), v)]))];
    let matches = candidates.filter(v => files.includes(v));
    if (!matches.length) matches = files.filter(f => variants.some(v => f === v || f.endsWith('/' + v)));
    if (matches.length !== 1) throw new Error(`${matches.length ? 'Ambiguous' : 'Missing'} reference: ${reference}`);
    return { name: matches[0], fragment };
  }

  const previous = await jsonOr(path.join(output, 'state.json'), { history: {} });
  const history = structuredClone(previous.history);
  const wrappers = new Map();
  const folders = new Map();
  const usedIds = new Set();
  const outputs = new Map();
  const put = (name, bytes) => outputs.set(name, Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes));
  for (const name of files.filter(f => f.startsWith(blog + '/') && f.endsWith('.md')).sort()) {
    const relative = name.slice(blog.length + 1);
    const parts = relative.split('/');
    if (parts.at(-1).startsWith('_') && parts.at(-1) !== '_index.md') continue;
    if (name.includes('.sync-conflict-')) throw new Error('Resolve Blog Syncthing conflicts first');
    const source = (await read(name)).toString('utf8').replace(/^\uFEFF/, '');
    if (source.startsWith('---') && !/^---[ \t]*\r?\n/.test(source))
      throw new Error('Article frontmatter must use YAML delimiters without an executable language');
    let parsed;
    try { parsed = matter(source); } catch { throw new Error(`Invalid article/folder YAML: ${relative}`); }
    const { data, content } = parsed;
    if (parts.at(-1) === '_index.md') {
      if (parts.length < 2 || parts.length > 3) throw new Error('Blog has exactly menu/topic/article levels');
      if (!data.id || !data.title || !data.slug) throw new Error('Folder needs id, title and slug');
      if (!['list', 'cards'].includes(data.view ?? 'list')) throw new Error('Folder view must be list or cards');
      data.id = uuid(String(data.id));
      const safe = Object.fromEntries(['id', 'title', 'slug', 'description', 'order', 'view', 'aliases', 'articles']
        .filter(key => data[key] !== undefined).map(key => [key, data[key]]));
      folders.set(parts.slice(0, -1).join('/'), safe);
      for (const mode of ['preview', 'published']) put(`${mode}/interests/${relative}`, matter.stringify('', safe));
      continue;
    }
    // Folder Notes / Waypoint create navigation notes automatically. Only templates opt in.
    if (data.status === undefined && data.id === undefined) continue;
    if (parts.length !== 3) throw new Error('Place article wrappers directly inside Blog/menu/topic');
    if (!data.id || !data.publishedAt) throw new Error('Article needs id and publishedAt; use a Blog template');
    if (!['draft', 'published'].includes(data.status)) throw new Error('Article status must be draft or published');
    data.title ||= path.posix.basename(name, '.md');
    if (!data.description && data.status === 'published') throw new Error('Published articles need a description');
    data.description ||= 'Draft preview.';
    if (typeof data.title !== 'string' || typeof data.description !== 'string' || data.description.length > 180)
      throw new Error('Use a text title and description of at most 180 characters');
    if (data.tags && (!Array.isArray(data.tags) || data.tags.some(t => typeof t !== 'string' || !t.trim())))
      throw new Error('tags must be a list of nonempty text values');
    data.publishedAt = date(data.publishedAt);
    if (data.updatedAt) data.updatedAt = date(data.updatedAt);
    if (!['article', 'poem', 'project'].includes(data.kind ?? 'article')) throw new Error('Invalid article kind');
    const id = uuid(String(data.id));
    if (usedIds.has(id)) throw new Error('Duplicate article id; create a new template instead of copying an identity');
    usedIds.add(id);
    const topic = parts.slice(0, 2).join('/');
    const url = data.url || history[id]?.current || `/${topic}/${slug(data.title)}`;
    if (!/^\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*$/.test(url)) throw new Error('Invalid article URL');
    const aliases = data.aliases ?? [];
    if (!Array.isArray(aliases)) throw new Error('aliases must be a list');
    history[id] = { current: url, paths: [...new Set([...(history[id]?.paths ?? []), ...aliases, url])].sort() };
    wrappers.set(name, { name, relative, topic, data, content, id, url });
  }
  if (!folders.size) throw new Error('Blog folder structure is missing; retain the last good preview');
  const claims = new Map();
  for (const [id, entry] of Object.entries(history)) for (const url of entry.paths) {
    if (claims.has(url) && claims.get(url) !== id) throw new Error('A URL already belongs to another article');
    claims.set(url, id);
  }
  const manifest = [];
  for (const wrapper of wrappers.values()) {
    const { name, relative, topic, data, content, id, url } = wrapper;
    const folder = folders.get(topic);
    if (!folder || !folders.has(topic.split('/')[0])) throw new Error('Article needs menu and topic _index.md notes');
    const assets = new Map();
    async function asset(reference, from, imageOnly = false) {
      const { name: target } = resolve(reference, from);
      if (!(imageOnly ? images : media).test(target)) throw new Error('Unsupported local attachment');
      const bytes = await read(target);
      const isImage = images.test(target);
      // Re-encode pictures: normalize orientation, bound size, discard EXIF/GPS and SVG active content.
      const encoded = isImage ? await sharp(bytes, { limitInputPixels: 80000000 }).rotate()
        .resize({ width: 1600, height: 1600, fit: 'inside', withoutEnlargement: true }).webp({ quality: 85 }).toBuffer() : bytes;
      const filename = `${hash(encoded).slice(0, 24)}${isImage ? '.webp' : path.extname(target).toLowerCase()}`;
      const destination = `images/${id}/${filename}`;
      assets.set(`${topic}/${destination}`, encoded);
      return destination;
    }
    async function expand(nodes, from, stack) {
      if (stack.length > 20) throw new Error('Embedded note depth exceeds 20');
      const result = [];
      for (const original of nodes) {
        let node = structuredClone(original);
        if (node.type === 'wikiLink' || node.type === 'embed') {
          const ref = node.value;
          const { name: target, fragment } = resolve(ref, from, true);
          const label = node.data?.alias || path.posix.basename(target, '.md');
          if (node.type === 'embed' && target.endsWith('.md')) {
            const key = `${target}#${fragment}`;
            if (stack.includes(key)) throw new Error('Circular note embed');
            const body = bodyOnly((await read(target)).toString('utf8'));
            const children = section(parseBody(body).children, fragment);
            result.push(...await expand(children, target, [...stack, key]));
            continue;
          }
          if (target.endsWith('.md')) {
            const linked = wrappers.get(target);
            // Private note links remain readable text; they do not publish the target.
            node = linked && !(data.status === 'published' && linked.data.status !== 'published')
              ? { type: 'link', url: linked.url + (fragment ? '#' + slug(fragment) : ''), children: [{ type: 'text', value: label }] }
              : { type: 'text', value: label };
          } else {
            const dest = await asset(ref, from);
            node = images.test(target) && original.type === 'embed'
              ? { type: 'image', url: dest, alt: /^\d+(?:x\d+)?$/.test(label) ? '' : label }
              : { type: 'link', url: dest, children: [{ type: 'text', value: label }] };
          }
        } else if ((node.type === 'image' || node.type === 'link' || node.type === 'definition') && node.url) {
          if (/^(?:https?:|mailto:|tel:|#)/i.test(node.url)) {
            // Ordinary web and YouTube links remain external; no remote fetching.
          } else if (/^[a-z][a-z\d+.-]*:|^\/\//i.test(node.url)) throw new Error('Unsupported link protocol');
          else {
            const { name: target, fragment } = resolve(node.url, from, node.type !== 'image');
            if (target.endsWith('.md')) {
              const linked = wrappers.get(target);
              if (linked && !(data.status === 'published' && linked.data.status !== 'published'))
                node.url = linked.url + (fragment ? '#' + slug(fragment) : '');
              else if (node.type === 'definition') throw new Error('Reference-style links to private notes are unsupported; use a wikilink');
              else node = { type: 'text', value: text(node) };
            } else node.url = await asset(node.url, from, node.type === 'image');
          }
        } else if (node.type === 'html') {
          // Vault notes are data, never executable MDX/HTML.
          node = { type: 'text', value: node.value.startsWith('<!--') ? '' : node.value };
        }
        if (node.children) {
          node.children = await expand(node.children, from, stack);
          if (node.type === 'paragraph' && node.children.some(n => !['text', 'image', 'link', 'strong', 'emphasis', 'delete', 'inlineCode', 'break', 'footnoteReference', 'linkReference', 'imageReference'].includes(n.type))) {
            const inline = [];
            const flush = () => { if (inline.length) result.push({ type: 'paragraph', children: inline.splice(0) }); };
            for (const child of node.children) {
              if (['paragraph', 'heading', 'list', 'blockquote', 'code', 'table', 'thematicBreak', 'definition'].includes(child.type)) { flush(); result.push(child); }
              else inline.push(child);
            }
            flush(); continue;
          }
        }
        result.push(node);
      }
      return result;
    }
    const expanded = await expand(parseBody(content).children, name, [name + '#']);
    const frontmatter = {
      id, url, aliases: history[id].paths.filter(p => p !== url), title: data.title,
      slug: url.split('/').at(-1), kind: data.kind ?? 'article', description: data.description,
      publishedAt: data.publishedAt, draft: data.status !== 'published', tags: data.tags ?? [],
      ...(data.updatedAt ? { updatedAt: data.updatedAt } : {}),
    };
    if (data['cover-media']) {
      frontmatter.coverImage = await asset(data['cover-media'], name, true);
      if (typeof data['cover-alt'] !== 'string' || data['cover-alt'].trim().length < 5) throw new Error('A cover needs descriptive cover-alt text');
      frontmatter.coverAlt = data['cover-alt'];
    } else if (folder.view === 'cards' && data.status === 'published') throw new Error('Published grid articles need cover-media and cover-alt');
    const markdown = matter.stringify(serializeBody(expanded), frontmatter);
    for (const mode of ['preview', ...(data.status === 'published' ? ['published'] : [])]) {
      put(`${mode}/interests/${relative}`, markdown);
      for (const [file, bytes] of assets) put(`${mode}/interests/${file}`, bytes);
    }
    manifest.push({ id, url, title: data.title, status: data.status, source: relative });
  }
  // Re-read every dependency: changes to embedded notes or images invalidate this snapshot too.
  for (const [name, digest] of inputs) if (hash(await readFile(path.join(vault, name))) !== digest)
    throw new Error('Source changed during export; retaining the last good preview');
  const finalFiles = files.filter(f => f.startsWith(blog + '/') && f.endsWith('.md')).sort();
  const currentFiles = [];
  async function rescan(dir) {
    for (const item of await readdir(path.join(vault, dir), { withFileTypes: true })) {
      if (item.name.startsWith('.')) continue;
      const name = path.posix.join(dir, item.name);
      if (item.isDirectory()) await rescan(name);
      else if (item.isFile() && name.endsWith('.md')) currentFiles.push(name);
    }
  }
  await rescan(blog);
  if (JSON.stringify(finalFiles) !== JSON.stringify(currentFiles.sort())) throw new Error('Blog changed during export');
  put('history.json', JSON.stringify(history, null, 2) + '\n');
  put('manifest.json', JSON.stringify(manifest, null, 2) + '\n');
  const checksums = Object.fromEntries([...outputs].sort(([a], [b]) => a.localeCompare(b)).map(([name, bytes]) => [name, hash(bytes)]));
  const revision = hash(JSON.stringify(checksums));
  await mkdir(output, { recursive: true, mode: 0o700 });
  const snapshot = path.join(output, revision);
  await mkdir(snapshot, { recursive: true, mode: 0o700 });
  for (const [name, bytes] of outputs) {
    const destination = path.join(snapshot, name);
    await mkdir(path.dirname(destination), { recursive: true, mode: 0o700 });
    try {
      await writeFile(destination, bytes, { flag: 'wx', mode: 0o600 });
    } catch (error) {
      if (error.code !== 'EEXIST' || hash(await readFile(destination)) !== hash(bytes)) throw error;
    }
  }
  await atomic(path.join(snapshot, 'checksums.json'), checksums);
  await atomic(path.join(output, 'state.json'), { history });
  await atomic(path.join(output, 'current.json'), { revision, articles: manifest.length, published: manifest.filter(a => a.status === 'published').length });
  return { revision, articles: manifest.length };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [vault, output] = process.argv.slice(2);
  if (!vault || !output) throw new Error('Usage: node export.mjs VAULT OUTPUT');
  try { console.log(JSON.stringify(await exportVault({ vault, output }))); }
  catch (error) { console.error(`Blog export failed: ${error.message}`); process.exitCode = 1; }
}
