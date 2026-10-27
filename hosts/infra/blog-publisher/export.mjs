import { createHash } from 'node:crypto';
import { readFile, readdir, realpath, lstat, mkdir, writeFile, rename, link } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import matter from 'gray-matter';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkStringify from 'remark-stringify';
import wikiLink from '@flowershow/remark-wiki-link';
import LZString from 'lz-string';

const parser = unified().use(remarkParse).use(remarkGfm).use(wikiLink);
const writer = unified().use(remarkStringify, { bullet: '-', unsafe: [
  { character: '{', inConstruct: ['phrasing'] },
  { character: '}', inConstruct: ['phrasing'] },
] }).use(remarkGfm);
const images = /\.(?:jpe?g|png|webp|avif|tiff?|gif|svg)$/i;
const media = /\.(?:jpe?g|png|webp|avif|tiff?|gif|svg|mp4|webm|pdf)$/i;
const mapAttachment = name => media.test(name) || /\.ipynb$/i.test(name);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const slug = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const label = value => value.replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
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
function cleanBody(source) {
  const protectedRanges = codeRanges(source);
  const markers = [...source.matchAll(/%%/g)].map(m => m.index)
    .filter(offset => !protectedRanges.some(([start, end]) => offset >= start && offset < end));
  if (markers.length % 2) throw new Error('Unterminated Obsidian comment');
  for (let i = markers.length - 2; i >= 0; i -= 2) source = source.slice(0, markers[i]) + source.slice(markers[i + 1] + 2);
  return source;
}
function parseBody(source) { return parser.parse(cleanBody(source)); }
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

export async function exportVault({ vault, output, blog = 'Blog', quietMs = 0, changedFiles = null }) {
  const started = performance.now();
  vault = await realpath(vault);
  const previous = await jsonOr(path.join(output, 'state.json'), { history: {} });
  const cache = path.join(output, '.source-cache');
  await mkdir(cache, { recursive: true, mode: 0o700 });
  const signature = stat => [stat.size, stat.mtimeMs, stat.ctimeMs, stat.ino].join(':');
  const inputStats = {};
  let sourceReadBytes = 0;
  const changed = name => changedFiles === null || changedFiles.some(item => name === item || name.startsWith(item + '/'));
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
  if (changedFiles !== null && previous.files) {
    files.push(...previous.files.filter(name => !changed(name)));
    for (const name of [...new Set(changedFiles)]) {
      if (name.split('/').some(part => part.startsWith('.')) || path.isAbsolute(name)) continue;
      try {
        const info = await lstat(path.join(vault, name));
        if (info.isDirectory()) await scan(name);
        else if (info.isFile()) files.push(name);
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
    files.splice(0, files.length, ...new Set(files));
  } else await scan();
  const indexed = performance.now();
  const conflicts = new Set(files.filter(name => name.includes('.sync-conflict-')).map(name => name.replace(/\.sync-conflict-[^.]+(?=\.[^.]+$)/, '')));
  const inputs = new Map();
  const sourceBytes = new Map();
  async function read(name) {
    if (sourceBytes.has(name)) return sourceBytes.get(name);
    if (conflicts.has(name)) throw new Error('Resolve the referenced Syncthing conflict first');
    // Index events identify changed paths; unchanged selected files live in the SSD cache.
    if (!changed(name) && previous.inputs?.[name]) {
      try {
        const bytes = await readFile(path.join(cache, previous.inputs[name]));
        inputs.set(name, previous.inputs[name]);
        inputStats[name] = previous.inputStats[name];
        sourceBytes.set(name, bytes);
        return bytes;
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
    const file = path.resolve(vault, name);
    const actual = await realpath(file);
    if (!actual.startsWith(vault + path.sep) || actual !== file || name.split('/').some(p => p.startsWith('.')))
      throw new Error('Reference escapes the vault or uses a symlink/hidden path');
    if (name.includes('.sync-conflict-')) throw new Error('Resolve the referenced Syncthing conflict first');
    const stat = await lstat(file);
    if (!stat.isFile() || (quietMs > 0 && Date.now() - stat.mtimeMs < quietMs)) throw new Error('Referenced files are still changing; retry after sync settles');
    inputStats[name] = signature(stat);
    let bytes, digest = previous.inputs?.[name];
    if (previous.inputStats?.[name] === inputStats[name] && digest) {
      try { bytes = await readFile(path.join(cache, digest)); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
    if (!bytes) {
      bytes = await readFile(file);
      sourceReadBytes += bytes.length;
      digest = hash(bytes);
      try { await writeFile(path.join(cache, digest), bytes, { flag: 'wx', mode: 0o600 }); }
      catch (error) { if (error.code !== 'EEXIST') throw error; }
    }
    inputs.set(name, digest);
    sourceBytes.set(name, bytes);
    return bytes;
  }
  async function readAsset(name) {
    const digest = previous.inputs?.[name];
    if (digest && !conflicts.has(name)) {
      const file = path.resolve(vault, name);
      if (!changed(name) || (await realpath(file) === file && signature(await lstat(file)) === previous.inputStats?.[name])) {
        const cachePath = path.join(cache, digest);
        try {
          await lstat(cachePath);
          inputs.set(name, digest);
          inputStats[name] = previous.inputStats[name];
          return { cachePath, digest };
        } catch (error) { if (error.code !== 'ENOENT') throw error; }
      }
    }
    await read(name);
    return { cachePath: path.join(cache, inputs.get(name)), digest: inputs.get(name) };
  }
  function resolve(reference, from, note = false) {
    reference = decodeURIComponent(reference).replace(/^!?(?:\[\[)([\s\S]*?)\]\]$/, '$1').split('|')[0].trim();
    const [target, fragment = ''] = reference.split('#', 2);
    if (!target) return { name: from, fragment };
    if (/^(?:[a-z][a-z\d+.-]*:|\/\/|\/)/i.test(target)) throw new Error('Use a vault-relative local reference');
    const variants = note ? [target, target + '.md'] : [target];
    const candidates = [...new Set(variants.flatMap(v => [path.posix.normalize(v), path.posix.join(path.posix.dirname(from), v)]))];
    let matches = candidates.filter(v => files.includes(v));
    if (!matches.length) {
      matches = files.filter(f => variants.some(v => f === v || f.endsWith('/' + v)));
      if (matches.length > 1) {
        // Prefer the shortest relative path; equally close basename matches still fail.
        const parents = path.posix.dirname(from).split('/');
        const proximity = name => {
          const parts = path.posix.dirname(name).split('/');
          let shared = 0;
          while (shared < Math.min(parts.length, parents.length) && parts[shared] === parents[shared]) shared++;
          return shared * 2 - parts.length;
        };
        const nearest = Math.max(...matches.map(proximity));
        matches = matches.filter(name => proximity(name) === nearest);
      }
    }
    if (matches.length !== 1) throw new Error(`${matches.length ? 'Ambiguous' : 'Missing'} reference: ${reference}`);
    return { name: matches[0], fragment };
  }

  const implementation = hash(Buffer.concat([await readFile(fileURLToPath(import.meta.url)), await readFile(new URL('package-lock.json', import.meta.url))]));
  if (previous.implementation === implementation && previous.inputs && JSON.stringify(previous.files) === JSON.stringify(files.sort())) {
    let unchanged = true;
    for (const name of Object.keys(previous.inputs).filter(changed)) {
      try { if (signature(await lstat(path.join(vault, name))) !== previous.inputStats?.[name]) { unchanged = false; break; } }
      catch (error) { if (error.code !== 'ENOENT') throw error; unchanged = false; break; }
    }
    if (unchanged &&
        (await jsonOr(path.join(output, 'current.json'), {})).revision === previous.revision)
      return { revision: previous.revision, articles: previous.articles, unchanged: true, sourceReadBytes: 0, elapsedMs: Math.round(performance.now() - started) };
  }
  const history = structuredClone(previous.history);
  function remember(id, url, aliases = []) {
    if (!Array.isArray(aliases)) throw new Error('aliases must be a list');
    const paths = [...new Set([...(history[id]?.paths ?? []), history[id]?.current, ...aliases, url].filter(p => p !== undefined))].sort();
    if (paths.some(p => typeof p !== 'string' || !/^\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*$/.test(p)))
      throw new Error('Invalid publication URL');
    history[id] = { current: url, paths };
    return paths.filter(p => p !== url);
  }
  const wrappers = new Map();
  const folders = new Map();
  const usedIds = new Set();
  const outputs = new Map();
  const collections = { preview: [], published: [] };
  const warnings = [];
  const mapHistory = structuredClone(previous.maps ?? {});
  const collectionCache = {};
  let reusedMaps = 0;
  const oldFileSet = new Set(previous.files ?? []);
  const addedBasenames = new Set(files.filter(name => !oldFileSet.has(name)).map(name => path.posix.basename(name)));
  const put = (name, bytes) => outputs.set(name, bytes?.cachePath || Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes));
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
      if (!data.id) throw new Error('Folder needs id');
      data.title = label(parts.at(-2));
      if (!['list', 'cards'].includes(data.view ?? 'list')) throw new Error('Folder view must be list or cards');
      data.id = uuid(String(data.id));
      if (usedIds.has(data.id)) throw new Error('Duplicate folder id');
      usedIds.add(data.id);
      const safe = Object.fromEntries(['id', 'title', 'slug', 'description', 'order', 'view', 'aliases', 'articles']
        .filter(key => data[key] !== undefined).map(key => [key, data[key]]));
      folders.set(parts.slice(0, -1).join('/'), safe);
      if (data.slug === 'about' && parts.length === 2) {
        wrappers.set(name, { name, relative, topic: parts[0], data: { ...safe, status: 'published' },
          content, id: safe.id, url: '/about', folderBody: true });
        continue;
      }
      continue;
    }
    // Folder Notes / Waypoint create navigation notes automatically. Only templates opt in.
    if (data.status === undefined && data.id === undefined) continue;
    if (parts.length !== 3) throw new Error('Place article wrappers directly inside Blog/menu/topic');
    if (!data.id || !data.publishedAt) throw new Error('Article needs id and publishedAt; use a Blog template');
    if (!['draft', 'published'].includes(data.status)) throw new Error('Article status must be draft or published');
    data.title = path.posix.basename(name, '.md');
    data.description ??= '';
    if (typeof data.title !== 'string' || typeof data.description !== 'string' || data.description.length > 180)
      throw new Error('Use a text title and description of at most 180 characters');
    if (data.tags && (!Array.isArray(data.tags) || data.tags.some(t => typeof t !== 'string' || !t.trim())))
      throw new Error('tags must be a list of nonempty text values');
    data.publishedAt = date(data.publishedAt);
    if (data.updatedAt) data.updatedAt = date(data.updatedAt);
    if (!['article', 'poem', 'project', 'gallery'].includes(data.kind ?? 'article')) throw new Error('Invalid article kind');
    const id = uuid(String(data.id));
    if (usedIds.has(id)) throw new Error('Duplicate article id; create a new template instead of copying an identity');
    usedIds.add(id);
    const topic = parts.slice(0, 2).join('/');
    const url = `/${parts.slice(0, 2).map(slug).join('/')}/${slug(data.title)}`;
    const aliases = data.aliases ?? [];
    if (!Array.isArray(aliases)) throw new Error('aliases must be a list');
    remember(id, url, [...aliases, ...(data.url ? [data.url] : [])]);
    wrappers.set(name, { name, relative, topic, data, content, id, url });
  }
  if (!folders.size) throw new Error('Blog folder structure is missing; retain the last good preview');
  // Retain pre-migration slugs before replacing any parent or child metadata.
  const legacyRoutes = new Map([...folders.keys()].map(name => [name, '/' + name.split('/').map((part, index, parts) =>
    folders.get(parts.slice(0, index + 1).join('/'))?.slug ?? slug(part)).join('/')]));
  for (const [name, data] of folders) {
    const url = '/' + name.split('/').map(slug).join('/');
    if (data.aliases !== undefined && !Array.isArray(data.aliases)) throw new Error('aliases must be a list');
    data.aliases = remember(data.id, url, [...(data.aliases ?? []), legacyRoutes.get(name)]);
    data.slug = slug(name.split('/').at(-1));
  }
  // Current routes win over old redirects, including URLs reused after deletion.
  const claims = new Map();
  const active = new Set([...wrappers.values()].map(w => w.id).concat([...folders.values()].map(f => f.id)));
  for (const id of active) {
    const url = history[id].current;
    if (claims.has(url) && claims.get(url) !== id) throw new Error('Two current articles or folders have the same URL');
    claims.set(url, id);
  }
  for (const [id, entry] of Object.entries(history)) entry.paths = entry.paths.filter(url => !claims.has(url) || claims.get(url) === id);
  for (const [name, data] of folders) {
    data.aliases = history[data.id].paths.filter(url => url !== history[data.id].current);
    for (const mode of ['preview', 'published']) put(`${mode}/interests/${name}/_index.md`, matter.stringify('', data));
  }
  const manifest = [];
  for (const wrapper of wrappers.values()) {
    const { name, relative, topic, data, content, id, url, folderBody } = wrapper;
    const folder = folders.get(topic);
    if (!folder || !folders.has(topic.split('/')[0])) throw new Error('Article needs menu and topic _index.md notes');
    const assets = new Map();
    const maps = [];
    const components = [];
    const startingNote = data['starting-note'] ?? '';
    if (typeof startingNote !== 'string') throw new Error('starting-note must be a note name or path');

    async function collectMap(entrypoint) {
      const collectionId = data['map-id'] ?? ('map-' + hash(id + ':' + maps.length).slice(0, 16));
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(collectionId)) throw new Error('Invalid map-id');
      const fingerprint = hash(JSON.stringify([implementation, data, entrypoint, url, history[id]]));
      const saved = previous.collections?.[collectionId];
      function emit(config, selected) {
        maps.push({ config, selected });
        const base = url + '/maps/' + collectionId;
        const token = 'BLOGMAPCOMPONENT' + components.length + hash(entrypoint).slice(0, 16);
        components.push([token, '<ObsidianMap title=' + JSON.stringify(data.title + ' mind map') + ' collectionUrl=' + JSON.stringify(base + '/collection.json') + ' indexUrl=' + JSON.stringify(base + '/index.html') + ' startingNote={' + JSON.stringify(startingNote.trim()) + '} />']);
        return { type: 'paragraph', children: [{ type: 'text', value: token }] };
      }
      let reusable = saved?.fingerprint === fingerprint && !saved.outputs.some(([name]) => addedBasenames.has(path.posix.basename(name)));
      if (reusable) {
        for (const name of Object.keys(saved.inputs)) {
          try {
            if (conflicts.has(name) || (changed(name) && signature(await lstat(path.join(vault, name))) !== saved.stats[name])) { reusable = false; break; }
          } catch (error) { if (error.code !== 'ENOENT') throw error; reusable = false; break; }
        }
      }
      if (reusable) {
        try { await Promise.all(saved.outputs.map(([, digest]) => lstat(path.join(cache, digest)))); }
        catch (error) { if (error.code !== 'ENOENT') throw error; reusable = false; }
      }
      if (reusable) {
        for (const [name, digest] of Object.entries(saved.inputs)) { inputs.set(name, digest); inputStats[name] = saved.stats[name]; }
        mapHistory[collectionId] = saved.history;
        warnings.push(...saved.warnings);
        collectionCache[collectionId] = saved;
        reusedMaps++;
        return emit(saved.config, new Map(saved.outputs.map(([name, digest]) => [name, { digest, cachePath: path.join(cache, digest) }])));
      }
      const warningStart = warnings.length;
      const selected = new Map();
      const scenes = new Map();
      const targets = new Map();
      const references = {};
      async function select(reference, from, isNote = true) {
        let target;
        const requestedTarget = decodeURIComponent(reference).replace(/^!?\[\[|\]\]$/g, '').split(/[|#]/)[0].trim();
        const requestedLink = decodeURIComponent(reference).replace(/^!?\[\[|\]\]$/g, '').split('|')[0].trim();
        const override = data['map-links']?.[from + '::' + requestedLink] ?? data['map-links']?.[from + '::' + requestedTarget] ?? data['map-links']?.[requestedTarget];
        if (override !== undefined && typeof override !== 'string') throw new Error('Map link overrides must be vault paths');
        try { target = resolve(override ?? reference, from, isNote).name; }
        catch (error) {
          const requested = decodeURIComponent(reference).replace(/^!?\[\[|\]\]$/g, '').split(/[|#]/)[0].trim();
          if (!error.message.startsWith('Missing reference:') || !isNote || mapAttachment(requested)) throw error;
          const filename = requested.endsWith('.md') ? requested : requested + '.md';
          target = path.posix.normalize(filename.includes('/') && !filename.startsWith('.') ? filename : path.posix.join(path.posix.dirname(from), filename));
          if (target.startsWith('../') || path.posix.isAbsolute(target)) throw error;
          warnings.push({ article: url, source: from, reference: requested });
          selected.set(target, Buffer.from('---\n---\n> [!warning] Note unavailable\n> This linked note is missing from the source vault. Correct its link in Obsidian to restore it.\n'));
        }
        targets.set(from + ':' + reference, target);
        (references[from] ??= {})[requestedLink] = target;
        await collect(target);
      }
      async function collect(target) {
        if (selected.has(target)) return;
        const bytes = target.endsWith('.md') ? await read(target) : await readAsset(target);
        selected.set(target, bytes);
        if (!target.endsWith('.md')) {
          if (!mapAttachment(target)) throw new Error('Unsupported map attachment: ' + target);
          return;
        }
        const body = bodyOnly(bytes.toString('utf8'));
        const fence = body.match(/```(compressed-json|json)\s*\n([\s\S]*?)```/);
        let scene;
        if (fence) {
          const decoded = fence[1] === 'compressed-json' ? LZString.decompressFromBase64(fence[2].replace(/\s/g, '')) : fence[2];
          try { const parsed = JSON.parse(decoded); if (parsed.type === 'excalidraw') scene = parsed; } catch { /* ordinary code fence */ }
        }
        if (scene) {
          scenes.set(target, scene);
          selected.set(target, Buffer.from('---\nexcalidraw-plugin: parsed\n---\n```json\n' + JSON.stringify(scene) + '\n```\n'));
          for (const element of scene.elements) {
            if (element.isDeleted || !element.link?.startsWith('[[')) continue;
            await select(element.link, target);
          }
        } else {
          const tree = parseBody(body);
          selected.set(target, Buffer.from('---\n---\n' + cleanBody(body)));
          async function visit(node) {
            if (node.type === 'embed' || node.type === 'wikiLink') {
              // Follow the selected map's complete local reference graph, with cycle deduplication.
              await select(node.value.replace(/\\$/, ''), target);
            } else if (['link', 'image', 'definition'].includes(node.type) && node.url && !/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(node.url)) {
              await select(node.url, target, node.type !== 'image');
            }
            for (const child of node.children ?? []) await visit(child);
          }
          await visit(tree);
        }
      }
      await collect(entrypoint);
      if (!scenes.has(entrypoint)) throw new Error('Map embed has no Excalidraw scene');
      const retained = data['map-include'] ?? [];
      if (!Array.isArray(retained) || retained.some(reference => typeof reference !== 'string'))
        throw new Error('map-include must be a list of vault note links');
      for (const reference of retained) await select(reference, entrypoint);
      // The ledger is publisher appdata: normal vault notes never receive IDs.
      const old = mapHistory[collectionId] ?? {};
      const previousNotes = Object.values(old);
      const routes = {};
      const noteAliases = {};
      const used = new Set(Object.values(old).map(item => item.route));
      const assigned = new Set();
      for (const [source, bytes] of selected) {
        if (!source.endsWith('.md')) continue;
        const anchors = [...scenes.get(entrypoint).elements].filter(e => !e.isDeleted && e.link?.startsWith('[[') && targets.get(entrypoint + ':' + e.link) === source).map(e => e.id);
        const digest = hash(bytes);
        let matches = previousNotes.filter(item => item.source === source);
        if (!matches.length) matches = previousNotes.filter(item => !selected.has(item.source) && anchors.some(a => item.anchors?.includes(a)));
        if (!matches.length) matches = previousNotes.filter(item => !selected.has(item.source) && item.digest === digest);
        const prior = matches.length === 1 ? matches[0] : undefined;
        let route = prior?.route ?? (slug(path.posix.basename(source, '.md')) || 'note-' + hash(source).slice(0, 8));
        if (!prior && used.has(route)) route += '-' + hash(source).slice(0, 8);
        if (assigned.has(route)) throw new Error('Ambiguous map-note rename; retain distinct source identities');
        assigned.add(route);
        used.add(route);
        routes[source] = route;
        const sources = [...new Set([...(prior?.sources ?? (prior ? [prior.source] : [])), source])];
        old[route] = { source, sources, route, digest, anchors };
        for (const alias of sources) noteAliases[hash(alias).slice(0, 16)] = route;
      }
      mapHistory[collectionId] = old;
      const config = { id: collectionId, title: data.title, directory: collectionId, entrypoint, articleUrl: url, articleAliases: history[id].paths.filter(p => p !== url), noteRoutes: routes, noteAliases, references };
      const retainedOutputs = [];
      for (const [source, bytes] of selected) {
        const digest = bytes.cachePath ? bytes.digest : hash(bytes);
        if (!bytes.cachePath) {
          try { await writeFile(path.join(cache, digest), bytes, { flag: 'wx', mode: 0o600 }); }
          catch (error) { if (error.code !== 'EEXIST') throw error; }
        }
        retainedOutputs.push([source, digest]);
      }
      const dependencies = [...selected.keys()].filter(name => inputs.has(name));
      collectionCache[collectionId] = { fingerprint, config, history: old,
        inputs: Object.fromEntries(dependencies.map(name => [name, inputs.get(name)])),
        stats: Object.fromEntries(dependencies.map(name => [name, inputStats[name]])),
        outputs: retainedOutputs, warnings: warnings.slice(warningStart) };
      return emit(config, selected);
    }
    async function asset(reference, from, imageOnly = false) {
      if (folderBody) throw new Error('About supports text and note embeds; use external links for attachments');
      const { name: target } = resolve(reference, from);
      if (!(imageOnly ? images : media).test(target)) throw new Error('Unsupported local attachment');
      if (imageOnly && /\.tiff?$/i.test(target)) throw new Error('TIFF cannot be displayed by all website browsers; choose a JPEG, PNG, WebP, AVIF, GIF or SVG original');
      const bytes = await readAsset(target);
      // Authored photographs are served byte-for-byte, including their orientation metadata.
      const encoded = bytes;
      const filename = `${bytes.digest.slice(0, 24)}${path.extname(target).toLowerCase()}`;
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
            if (/^excalidraw-plugin:/m.test((await read(target)).toString('utf8').split('---')[1] ?? '')) {
              if (fragment || folderBody) throw new Error('Embed the whole map in an article');
              result.push(await collectMap(target));
              continue;
            }
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
            const dest = await asset(ref, from, images.test(target) && original.type === 'embed');
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
    if (data.kind === 'gallery') {
      const body = cleanBody(content).trim();
      if (!body.startsWith('---') || !body.endsWith('---'))
        throw new Error('A gallery uses --- on its own line before and after each photo block');
      const blocks = body.split(/^---[ \t]*$/m).filter(block => block.trim());
      if (!blocks.length) throw new Error('A gallery needs at least one photo');
      const galleryImages = {};
      const galleryFiles = new Map();
      for (const [index, block] of blocks.entries()) {
        const match = block.trim().match(/^!?\[\[([^\]\n]+)\]\]([\s\S]*)$/);
        if (!match) throw new Error('Start each gallery block with [[picture link]], followed by an optional description');
        const { name: target, fragment } = resolve(match[1], name);
        if (fragment || !images.test(target)) throw new Error('Gallery links must point to local image attachments');
        if (/\.tiff?$/i.test(target)) throw new Error('TIFF cannot be displayed by all website browsers; choose a JPEG, PNG, WebP, AVIF, GIF or SVG original for this gallery');
        const bytes = await readAsset(target);
        const filename = `${String(index + 1).padStart(4, '0')}-${bytes.digest.slice(0, 24)}${path.extname(target).toLowerCase()}`;
        const alias = match[1].split('|').slice(1).join('|').trim();
        const caption = match[2].trim();
        galleryImages[filename] = {
          alt: alias.length >= 5 ? alias : `Photo: ${path.posix.basename(target)}`,
          ...(caption ? { caption } : {}),
        };
        galleryFiles.set(filename, bytes);
      }
      const metadata = {
        id, url, aliases: history[id].paths.filter(p => p !== url), title: data.title,
        slug: url.split('/').at(-1), description: data.description,
        publishedAt: data.publishedAt, draft: data.status !== 'published', tags: data.tags ?? [],
        ...(data.updatedAt ? { updatedAt: data.updatedAt } : {}), images: galleryImages,
      };
      for (const mode of ['preview', ...(data.status === 'published' ? ['published'] : [])]) {
        const destination = `${mode}/interests/${topic}/${metadata.slug}`;
        put(`${destination}/gallery.json`, JSON.stringify(metadata, null, 2) + '\n');
        for (const [filename, bytes] of galleryFiles) put(`${destination}/${filename}`, bytes);
      }
      manifest.push({ id, url, title: data.title, status: data.status, source: relative });
      continue;
    }
    const expanded = await expand(parseBody(content).children, name, [name + '#']);
    if (folderBody) {
      const markdown = matter.stringify(serializeBody(expanded), folder);
      for (const mode of ['preview', 'published']) put(`${mode}/interests/${relative}`, markdown);
      continue;
    }
    const frontmatter = {
      id, url, aliases: history[id].paths.filter(p => p !== url), title: data.title,
      slug: url.split('/').at(-1), kind: data.kind ?? 'article', description: data.description,
      publishedAt: data.publishedAt, draft: data.status !== 'published', tags: data.tags ?? [],
      ...(maps.length ? { 'starting-note': startingNote.trim() } : {}),
      ...(data.updatedAt ? { updatedAt: data.updatedAt } : {}),
    };
    if (data['cover-media']) {
      frontmatter.coverImage = await asset(data['cover-media'], name, true);
      if (typeof data['cover-alt'] !== 'string' || data['cover-alt'].trim().length < 5) throw new Error('A cover needs descriptive cover-alt text');
      frontmatter.coverAlt = data['cover-alt'];
    } else if (folder.view === 'cards' && data.status === 'published') throw new Error('Published grid articles need cover-media and cover-alt');
    let rendered = serializeBody(expanded);
    for (const [token, component] of components) rendered = rendered.replaceAll(token, component);
    const markdown = matter.stringify(rendered, frontmatter);
    for (const mode of ['preview', ...(data.status === 'published' ? ['published'] : [])]) {
      put(`${mode}/interests/${maps.length ? relative.replace(/\.md$/, '.mdx') : relative}`, markdown);
      for (const { config, selected } of maps) {
        collections[mode].push(config);
        for (const [source, bytes] of selected) put(`${mode}/obsidian/${config.id}/${source}`, bytes);
      }
      for (const [file, bytes] of assets) put(`${mode}/interests/${file}`, bytes);
    }
    manifest.push({ id, url, title: data.title, status: data.status, source: relative });
  }
  // Later index events trigger the next export; unrelated writes do not delay this one.
  for (const mode of ['preview', 'published']) put(`${mode}/obsidian/collections.json`, JSON.stringify(collections[mode], null, 2) + '\n');
  put('warnings.json', JSON.stringify(warnings, null, 2) + '\n');
  put('map-history.json', JSON.stringify(mapHistory, null, 2) + '\n');
  put('history.json', JSON.stringify(history, null, 2) + '\n');
  put('manifest.json', JSON.stringify(manifest, null, 2) + '\n');
  const rendered = performance.now();
  const checksums = Object.fromEntries([...outputs].sort(([a], [b]) => a.localeCompare(b)).map(([name, bytes]) => [name, bytes.cachePath ? bytes.digest : hash(bytes)]));
  const revision = hash(JSON.stringify(checksums));
  await mkdir(output, { recursive: true, mode: 0o700 });
  const snapshot = path.join(output, revision);
  await mkdir(snapshot, { recursive: true, mode: 0o700 });
  const previousChecksums = previous.revision ? await jsonOr(path.join(output, previous.revision, 'checksums.json'), {}) : {};
  for (const [name, bytes] of outputs) {
    const destination = path.join(snapshot, name);
    await mkdir(path.dirname(destination), { recursive: true, mode: 0o700 });
    try {
      if (previousChecksums[name] === checksums[name]) await link(path.join(output, previous.revision, name), destination);
      else if (bytes.cachePath) await link(bytes.cachePath, destination);
      else await writeFile(destination, bytes, { flag: 'wx', mode: 0o600 });
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
    }
  }
  const checksumFile = path.join(snapshot, 'checksums.json');
  const checksumBytes = JSON.stringify(checksums, null, 2) + '\n';
  try { await writeFile(checksumFile, checksumBytes, { flag: 'wx', mode: 0o600 }); }
  catch (error) {
    if (error.code !== 'EEXIST' || await readFile(checksumFile, 'utf8') !== checksumBytes) throw error;
  }
  await atomic(path.join(output, 'state.json'), { implementation, history, maps: mapHistory, collections: collectionCache, inputs: Object.fromEntries(inputs), inputStats, files: files.sort(), revision, articles: manifest.length });
  const modes = Object.fromEntries(['preview', 'published'].map(mode => [mode, hash(JSON.stringify(Object.entries(checksums).filter(([name]) => name.startsWith(mode + '/'))))]));
  await atomic(path.join(output, 'current.json'), { revision, modes, articles: manifest.length, published: manifest.filter(a => a.status === 'published').length, exportedAt: new Date().toISOString() });
  return { revision, articles: manifest.length, unavailableNotes: warnings.length, reusedMaps, sourceReadBytes, elapsedMs: Math.round(performance.now() - started), timings: { indexMs: Math.round(indexed - started), renderMs: Math.round(rendered - indexed), writeMs: Math.round(performance.now() - rendered) } };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [vault, output] = process.argv.slice(2);
  if (!vault || !output) throw new Error('Usage: node export.mjs VAULT OUTPUT');
  let changedFiles = null;
  if (process.argv.includes('--changed-files-stdin')) {
    let input = '';
    for await (const chunk of process.stdin) input += chunk;
    changedFiles = JSON.parse(input);
  }
  try { console.log(JSON.stringify(await exportVault({ vault, output, changedFiles }))); }
  catch (error) { console.error(`Blog export failed: ${error.message}`); process.exitCode = 1; }
}
