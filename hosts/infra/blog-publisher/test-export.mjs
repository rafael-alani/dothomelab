import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, readdir, symlink, rename, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import sharp from 'sharp';
import { exportVault, bodyOnly } from './export.mjs';

async function fixture() {
  const root = await mkdtemp(path.join(os.tmpdir(), 'blog-export-'));
  const vault = path.join(root, 'vault'), output = path.join(root, 'output');
  async function put(name, value) {
    const file = path.join(vault, name);
    await mkdir(path.dirname(file), { recursive: true });
    await writeFile(file, value);
  }
  const meta = { id: 'my-stable-note', title: 'An article', description: 'A useful description.', publishedAt: '2026-10-25', status: 'draft' };
  const note = (body, extra = {}) => '---\n' + Object.entries({ ...meta, ...extra }).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join('\n') + '\n---\n' + body;
  await put('Blog/creativity/_index.md', '---\nid: 686abb4e-cbc3-4971-a695-169b6119e766\ntitle: Creativity\nslug: creativity\n---\n');
  await put('Blog/creativity/photography/_index.md', '---\nid: 808540ac-45c8-4183-8627-dcecdbef1fac\ntitle: Photography\nslug: photography\nview: cards\n---\n');
  await put('Blog/creativity/photography/article.md', note('![[Source]]'));
  await put('Notes/Source.md', '---\nsecret: [invalid YAML\nstatus: published\n---\n# Selected\nOriginal body.\n');
  const run = (changedFiles = null) => exportVault({ vault, output, quietMs: 0, changedFiles });
  const exported = async (result, name = 'preview/interests/creativity/photography/article.md') => readFile(path.join(output, result.revision, name), 'utf8');
  return { root, vault, output, put, note, run, exported };
}

test('embedded YAML is never parsed or rendered, drafts preview only, output is deterministic', async () => {
  const f = await fixture(), result = await f.run(), source = await f.exported(result);
  assert.match(source, /Original body/);
  assert.match(source, /draft: true/);
  assert.doesNotMatch(source, /secret|invalid YAML|status: published/);
  await assert.rejects(f.exported(result, 'published/interests/creativity/photography/article.md'), { code: 'ENOENT' });
  assert.equal((await f.run()).revision, result.revision);
  await f.put('Notes/Source.md', 'Changed embedded body.');
  assert.notEqual((await f.run()).revision, result.revision);
});
test('recreating a deleted article can reuse its URL without an obsolete identity blocking publication', async () => {
  const f = await fixture();
  await f.run();
  await f.put('Blog/creativity/photography/article.md', f.note('Replacement body.', { id: 'replacement' }));
  const result = await f.run();
  assert.match(await f.exported(result), /Replacement body/);
});
test('About folder body is editable, expands notes and keeps vault markup inert', async () => {
  const f = await fixture();
  const about = '---\nid: 7e85bf84-ad34-46c1-a0f2-a3e428bb36ab\ntitle: About\nslug: about\n---\n';
  await f.put('Blog/about/_index.md', about + '![[Source]]\n\n{danger()}\n\n<script>alert(1)</script>');
  const first = await f.run();
  const result = await f.exported(first, 'preview/interests/about/about.md');
  assert.match(result, /Original body/);
  assert.doesNotMatch(result, /secret|invalid YAML|(?<!\\)<script>|\n\{danger/);
  assert.equal(result, await f.exported(first, 'published/interests/about/about.md'));
  await f.put('Blog/about/_index.md', about + 'My updated biography.');
  const second = await f.run();
  assert.notEqual(second.revision, first.revision);
  assert.match(await f.exported(second, 'preview/interests/about/about.md'), /My updated biography/);
});
test('missing and empty descriptions stay empty for drafts and published articles', async () => {
  const f = await fixture();
  await f.put('Blog/creativity/photography/_index.md', '---\nid: 808540ac-45c8-4183-8627-dcecdbef1fac\nview: list\ndescription: ""\n---\n');
  for (const status of ['draft', 'published']) {
    for (const description of ['', undefined]) {
      let note = f.note('![[Source]]', { status, description });
      if (description === undefined) note = note.replace('description: undefined\n', '');
      await f.put('Blog/creativity/photography/article.md', note);
      const result = await f.run();
      const source = await f.exported(result);
      assert.match(source, /description: ['"]{2}/);
      assert.doesNotMatch(source, /Draft preview|A useful description/);
      if (status === 'published') assert.equal(source, await f.exported(result, 'published/interests/creativity/photography/article.md'));
    }
  }
});
test('deleting a topic removes its articles while retaining URL ownership', async () => {
  const f = await fixture();
  const first = await f.run();
  const history = JSON.parse(await f.exported(first, 'history.json'));
  await rm(path.join(f.vault, 'Blog/creativity/photography'), { recursive: true });
  const deleted = await f.run();
  assert.notEqual(deleted.revision, first.revision);
  const checksums = JSON.parse(await f.exported(deleted, 'checksums.json'));
  assert.equal(Object.keys(checksums).some(name => name.includes('/photography/')), false);
  assert.deepEqual(JSON.parse(await f.exported(deleted, 'manifest.json')), []);
  assert.deepEqual(JSON.parse(await f.exported(deleted, 'history.json')), history);
  assert.equal((await f.run()).revision, deleted.revision);
});
test('section and nested embeds resolve in their own folders, collect only referenced assets', async () => {
  const f = await fixture();
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source#Selected]]'));
  await f.put('Notes/Source.md', '# Selected\n![[Inner]]\n# Private\nDo not publish this.');
  await f.put('Notes/Inner.md', '---\nprivate: hidden\n---\n![Canal](../Assets/photo.png)');
  await f.put('Assets/photo.png', await sharp({ create: { width: 20, height: 10, channels: 3, background: 'red' } }).png().toBuffer());
  await f.put('Assets/unrelated.txt', 'private');
  const result = await f.run(), source = await f.exported(result);
  assert.doesNotMatch(source, /Do not publish|private:|unrelated/);
  assert.match(source, /!\[Canal\]\(images\//);
  const sums = JSON.parse(await f.exported(result, 'checksums.json'));
  assert.equal(Object.keys(sums).filter(p => p.endsWith('.png')).length, 1);
  await f.put('Assets/photo.png', await sharp({ create: { width: 20, height: 10, channels: 3, background: 'blue' } }).png().toBuffer());
  assert.notEqual((await f.run()).revision, result.revision);
});
test('published grid article requires a cover and alt, production excludes drafts and private YAML', async () => {
  const f = await fixture();
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source]]', { status: 'published' }));
  await assert.rejects(f.run(), /cover-media/);
  await f.put('Assets/cover.png', await sharp({ create: { width: 10, height: 10, channels: 3, background: 'green' } }).png().toBuffer());
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source]]', { status: 'published', 'cover-media': '[[Assets/cover.png]]', 'cover-alt': 'Green square' }));
  const result = await f.run();
  const publicNote = await f.exported(result, 'published/interests/creativity/photography/article.md');
  assert.match(publicNote, /draft: false/);
  assert.match(publicNote, /coverImage: images\//);
  assert.doesNotMatch(publicNote, /secret|cover-media/);
});
test('private ordinary links become text; code examples are not resolved; MDX expressions escaped', async () => {
  const f = await fixture();
  await f.put('Notes/Private.md', 'Never include this.');
  await f.put('Notes/Source.md', '[[Private|Other note]] and `{danger()}` and {danger()}\n\n```md\n![[Missing]]\n```\n\n<script>alert(1)</script>');
  const source = await f.exported(await f.run());
  assert.match(source, /Other note/);
  assert.doesNotMatch(source, /Never include|\[Other note\]\(/);
  assert.match(source, /\\\{danger\(\)\\\}/);
  assert.match(source, /!\[\[Missing\]\]/);
  assert.match(source, /\\<script>/);
});
test('cycle, missing, ambiguity, symlink and conflict fail without replacing current', async () => {
  const f = await fixture(), good = await f.run();
  for (const body of ['![[Missing]]', '![[Source]]']) {
    await f.put('Notes/Source.md', body);
    await assert.rejects(f.run(), /Missing|Circular/);
  }
  await f.put('Notes/Source.md', '![[Duplicate]]');
  await f.put('A/Duplicate.md', 'one'); await f.put('B/Duplicate.md', 'two');
  await assert.rejects(f.run(), /Ambiguous/);
  await symlink(path.join(f.vault, 'A/Duplicate.md'), path.join(f.vault, 'Notes/link.md'));
  await f.put('Notes/Source.md', '![[Notes/link.md]]');
  await assert.rejects(f.run(), /Missing|symlink/);
  await f.put('Notes/Source.md', 'valid');
  await f.put('Notes/Source.sync-conflict-20261025-120000-DEVICE.md', 'conflict');
  await assert.rejects(f.run(), /conflict/);
  assert.equal(JSON.parse(await readFile(path.join(f.output, 'current.json'))).revision, good.revision);
});
test('IDs preserve initial permalink on title edits, duplicate identities are rejected', async () => {
  const f = await fixture(), first = await f.run();
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source]]', { title: 'Changed title' }));
  assert.match(await f.exported(await f.run()), /url: \/creativity\/photography\/article/);
  await f.put('Blog/creativity/photography/copy.md', f.note('copy'));
  await assert.rejects(f.run(), /Duplicate article id/);
});
test('frontmatter stripping handles BOM, CRLF and alternate ending; rejects unterminated metadata', () => {
  assert.equal(bodyOnly('\uFEFF---\r\nbad: [\r\n...\r\nBody'), 'Body');
  assert.throws(() => bodyOnly('---\nprivate: hidden'), /unterminated/);
});
test('Waypoint folder notes are ignored, Obsidian comments stay private, code comments remain examples', async () => {
  const f = await fixture();
  await f.put('Blog/Blog.md', '%% Begin Waypoint %%\n[[Private]]\n%% End Waypoint %%');
  await f.put('Blog/creativity/photography/photography.md', '[[Navigation]]');
  await f.put('Notes/Source.md', 'Visible %%private aside%% prose.\n\n`%%example%%`');
  const result = await f.run(), source = await f.exported(result);
  assert.equal(result.articles, 1);
  assert.doesNotMatch(source, /private aside|Waypoint|Navigation/);
  assert.match(source, /%%example%%/);
});
test('ESM-looking prose cannot execute in the MDX build and unterminated comments fail closed', async () => {
  const f = await fixture();
  await f.put('Notes/Source.md', "import fs from 'node:fs'\n\nexport default 42\n\n```js\nimport fs from 'node:fs'\n```");
  const source = await f.exported(await f.run());
  assert.match(source, /&#105;mport fs/);
  assert.match(source, /&#101;xport default/);
  assert.match(source, /```js\nimport fs/);
  await f.put('Notes/Source.md', 'Visible %%private unfinished comment');
  await assert.rejects(f.run(), /Unterminated Obsidian comment/);
});
test('wrapper frontmatter cannot select gray-matter executable engines', async () => {
  const f = await fixture();
  globalThis.blogFrontmatterExecuted = false;
  await f.put('Blog/creativity/photography/article.md', '---javascript\n(globalThis.blogFrontmatterExecuted = true, {})\n---\ntext');
  await assert.rejects(f.run(), /without an executable language/);
  assert.equal(globalThis.blogFrontmatterExecuted, false);
});

test('maps collect five nested levels, deduplicate cycles, keep IDs out of vault and retain element routes on rename', async () => {
  const f = await fixture();
  const scene = {type: 'excalidraw', elements: [{id:'card', type:'embeddable', x:0,y:0,width:500,height:400,link:'[[Notes/one/two/three/four/five/Deep]]'}], appState: {}, files:{}};
  const drawing = () => '---\nexcalidraw-plugin: parsed\n---\n```json\n' + JSON.stringify(scene) + '\n```';
  await f.put('Map.md', drawing());
  await f.put('Notes/one/two/three/four/five/Deep.md', '---\nsecret: [invalid YAML\n---\nDeep content. ![[Leaf]]');
  await f.put('Notes/one/two/three/four/five/Leaf.md', 'Leaf content. [[Deep]]');
  await f.put('Blog/creativity/photography/article.md', f.note('![[Map]]', {'starting-note': 'Deep'}));
  const first = await f.run();
  const configs = JSON.parse(await f.exported(first, 'preview/obsidian/collections.json'));
  assert.equal(configs.length, 1);
  assert.deepEqual(JSON.parse(await f.exported(first, 'published/obsidian/collections.json')), []);
  const config = configs[0];
  assert.equal(config.noteRoutes['Notes/one/two/three/four/five/Deep.md'], 'deep');
  assert.match(await f.exported(first, 'preview/interests/creativity/photography/article.mdx'), /startingNote=\{"Deep"\}/);
  await f.put('Blog/creativity/photography/article.md', f.note('![[Map]]', {'starting-note': 7}));
  await assert.rejects(f.run(), /starting-note must be a note name or path/);
  await f.put('Blog/creativity/photography/article.md', f.note('![[Map]]', {'starting-note': ''}));
  assert.doesNotMatch(await f.exported(first, 'preview/obsidian/' + config.id + '/Notes/one/two/three/four/five/Deep.md'), /secret/);
  await f.put('Notes/one/two/three/four/five/Renamed.md', 'Edited and renamed.');
  scene.elements[0].link = '[[Notes/one/two/three/four/five/Renamed]]';
  await f.put('Map.md', drawing());
  const next = await f.run();
  const changed = JSON.parse(await f.exported(next, 'preview/obsidian/collections.json'))[0];
  assert.equal(changed.noteRoutes['Notes/one/two/three/four/five/Renamed.md'], 'deep');
  assert.notEqual(first.revision, next.revision);
  assert.doesNotMatch(await readFile(path.join(f.vault, 'Notes/one/two/three/four/five/Renamed.md'), 'utf8'), /id:/);
  await rename(path.join(f.vault, 'Blog/creativity/photography/article.md'), path.join(f.vault, 'Blog/creativity/photography/Renamed map.md'));
  const moved = JSON.parse(await f.exported(await f.run(), 'preview/obsidian/collections.json'))[0];
  assert.equal(moved.id, config.id);
  assert.equal(moved.articleUrl, '/creativity/photography/renamed-map');
  assert.deepEqual(moved.articleAliases, ['/creativity/photography/article']);
  assert.deepEqual(moved.noteRoutes, changed.noteRoutes);
});
test('folder and article renames update URLs while IDs retain all former addresses', async () => {
  const f = await fixture();
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source]]', { url: '/creativity/photography/article' }));
  await f.run();
  await rename(path.join(f.vault, 'Blog/creativity/photography/article.md'), path.join(f.vault, 'Blog/creativity/photography/Better name.md'));
  await rename(path.join(f.vault, 'Blog/creativity/photography'), path.join(f.vault, 'Blog/creativity/Pictures'));
  await rename(path.join(f.vault, 'Blog/creativity'), path.join(f.vault, 'Blog/Art'));
  const result = await f.run();
  const article = await f.exported(result, 'preview/interests/Art/Pictures/Better name.md');
  assert.match(article, /title: An article/);
  assert.match(article, /url: \/art\/pictures\/better-name/);
  assert.match(article, /- \/creativity\/photography\/article/);
  const folder = await f.exported(result, 'preview/interests/Art/Pictures/Pictures.md');
  assert.match(folder, /title: Photography/);
  assert.match(folder, /slug: pictures/);
  assert.match(folder, /- \/creativity\/photography/);
  const history = JSON.parse(await f.exported(result, 'history.json'));
  assert.equal(history['686abb4e-cbc3-4971-a695-169b6119e766'].current, '/art');
  await rename(path.join(f.vault, 'Blog/Art/Pictures'), path.join(f.vault, 'Blog/Art/Photos'));
  const next = await f.run();
  assert.match(await f.exported(next, 'preview/interests/Art/Photos/Photos.md'), /- \/art\/pictures/);
  await f.put('Blog/Art/Pictures/_index.md', '---\nid: 99999999-9999-4999-8999-999999999999\nslug: pictures\n---\n');
  const reused = await f.run();
  assert.doesNotMatch(await f.exported(reused, 'preview/interests/Art/Photos/Photos.md'), /- \/art\/pictures/);
  assert.match(await f.exported(reused, 'preview/interests/Art/Pictures/Pictures.md'), /slug: pictures/);
});
test('first export after a rename seeds legacy folder slugs and article URLs', async () => {
  const f = await fixture();
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source]]', { url: '/creativity/photography/original' }));
  await rename(path.join(f.vault, 'Blog/creativity/photography'), path.join(f.vault, 'Blog/creativity/Pictures'));
  await rename(path.join(f.vault, 'Blog/creativity'), path.join(f.vault, 'Blog/Art'));
  const result = await f.run();
  const history = JSON.parse(await f.exported(result, 'history.json'));
  assert.deepEqual(history['808540ac-45c8-4183-8627-dcecdbef1fac'], {
    current: '/art/pictures', paths: ['/art/pictures', '/creativity/photography'],
  });
  assert.match(await f.exported(result, 'preview/interests/Art/Pictures/article.md'), /- \/creativity\/photography\/original/);
});
test('missing map notes are explicit unavailable cards, identical notes retain distinct routes, mirrors do not win short links', async () => {
  const f = await fixture();
  const scene = {type:'excalidraw',elements:[
    {id:'missing',type:'embeddable',x:0,y:0,width:500,height:400,link:'[[Missing]]'},
    {id:'first',type:'embeddable',x:500,y:0,width:500,height:400,link:'[[Same]]'},
    {id:'second',type:'embeddable',x:1000,y:0,width:500,height:400,link:'[[Other]]'},
  ],appState:{},files:{}};
  await f.put('Notes/Map.md','---\nexcalidraw-plugin: parsed\n---\n```json\n'+JSON.stringify(scene)+'\n```');
  await f.put('Notes/Same.md','Identical body.');
  await f.put('Notes/Other.md','Identical body.');
  await f.put('Mirror/old/copy/Notes/Same.md','Wrong copy.');
  await f.put('Blog/creativity/photography/article.md',f.note('![[Notes/Map]]'));
  const result=await f.run();
  const config=JSON.parse(await f.exported(result,'preview/obsidian/collections.json'))[0];
  assert.notEqual(config.noteRoutes['Notes/Same.md'],config.noteRoutes['Notes/Other.md']);
  assert.match(await f.exported(result,`preview/obsidian/${config.id}/Notes/Missing.md`),/Note unavailable/);
  assert.equal(JSON.parse(await f.exported(result,'warnings.json')).length,1);
  assert.equal((await f.run()).revision,result.revision);
});
test('per-note PDF edition overrides retain fragments and exact source choices', async () => {
  const f=await fixture();
  const scene={type:'excalidraw',elements:[{id:'card',type:'embeddable',x:0,y:0,width:500,height:400,link:'[[Notes/Source]]'}],appState:{},files:{}};
  await f.put('Map.md','---\nexcalidraw-plugin: parsed\n---\n```json\n'+JSON.stringify(scene)+'\n```');
  await f.put('Notes/Source.md','![[lecture.pdf#page=2]]');
  await f.put('Editions/2025/lecture.pdf','old edition');
  await f.put('Editions/2026/lecture.pdf','new edition');
  await f.put('Blog/creativity/photography/article.md',f.note('![[Map]]',{'map-links':{'Notes/Source.md::lecture.pdf':'Editions/2025/lecture.pdf'}}));
  const result=await f.run();
  const config=JSON.parse(await f.exported(result,'preview/obsidian/collections.json'))[0];
  assert.equal(config.references['Notes/Source.md']['lecture.pdf#page=2'],'Editions/2025/lecture.pdf');
  assert.equal(await f.exported(result,`preview/obsidian/${config.id}/Editions/2025/lecture.pdf`),'old edition');
  await assert.rejects(f.exported(result,`preview/obsidian/${config.id}/Editions/2026/lecture.pdf`),{code:'ENOENT'});
});
test('canvas image dependencies retain file IDs, PDF fragments and publication boundaries', async t => {
  const f = await fixture();
  t.after(() => rm(f.root, { recursive: true, force: true }));
  await f.put('Blog/creativity/photography/_index.md', '---\nid: 808540ac-45c8-4183-8627-dcecdbef1fac\nview: list\n---\n');
  const scene = { type: 'excalidraw', elements: [
    { id: 'picture', type: 'image', fileId: 'raster', link: null },
    { id: 'excerpt', type: 'image', fileId: 'pdf', crop: { x: 4, y: 8, width: 40, height: 20 } },
    { id: 'deleted', type: 'image', fileId: 'private', isDeleted: true },
  ], appState: {}, files: {} };
  await f.put('Map.md', '---\nexcalidraw-plugin: parsed\n---\n## Embedded Files\n'
    + 'raster: [[image.png]]\npdf: [[lecture.pdf#page=4&rect=1,2,11,7]]\nprivate: [[private.png]]\n'
    + '## Drawing\n```json\n' + JSON.stringify(scene) + '\n```');
  await f.put('Assets/image.png', 'original pixels');
  await f.put('Assets/lecture.pdf', 'PDF');
  await f.put('Blog/creativity/photography/article.md', f.note('![[Map]]'));
  const first = await f.run();
  const [config] = JSON.parse(await f.exported(first, 'preview/obsidian/collections.json'));
  const prefix = `preview/obsidian/${config.id}/`;
  assert.match(await f.exported(first, prefix + 'Map.md'), /raster: \[\[image.png\]\]/);
  assert.doesNotMatch(await f.exported(first, prefix + 'Map.md'), /private: /);
  assert.equal(config.references['Map.md']['lecture.pdf#page=4&rect=1,2,11,7'], 'Assets/lecture.pdf');
  assert.equal(await f.exported(first, prefix + 'Assets/image.png'), 'original pixels');
  await assert.rejects(f.exported(first, prefix.replace('preview/', 'published/') + 'Assets/image.png'), { code: 'ENOENT' });
  await f.put('Assets/image.png', 'changed pixels');
  const changed = await f.run(['Assets/image.png']);
  assert.notEqual(changed.revision, first.revision);
  assert.equal(await f.exported(changed, prefix + 'Assets/image.png'), 'changed pixels');
  assert.equal((await f.run([])).revision, changed.revision);
  await f.put('Blog/creativity/photography/article.md', f.note('![[Map]]', { status: 'published' }));
  const published = await f.run();
  assert.equal(await f.exported(published, prefix.replace('preview/', 'published/') + 'Assets/image.png'), 'changed pixels');
  await rm(path.join(f.vault, 'Assets/image.png'));
  await assert.rejects(f.run(), /Missing reference: image.png/);
});
test('retained reading pages follow their live source even when no drawing element links them', async () => {
  const f=await fixture();
  const scene={type:'excalidraw',elements:[],appState:{},files:{}};
  await f.put('Map.md','---\nexcalidraw-plugin: parsed\n---\n```json\n'+JSON.stringify(scene)+'\n```');
  await f.put('Notes/Former reading page.md','Current vault content. [[Analysis.ipynb]]');
  await f.put('Notes/Analysis.ipynb','{"cells":[],"nbformat":4}');
  await f.put('Blog/creativity/photography/article.md',f.note('![[Map]]',{'map-include':['[[Notes/Former reading page]]']}));
  const first=await f.run();
  const config=JSON.parse(await f.exported(first,'preview/obsidian/collections.json'))[0];
  assert.equal(config.noteRoutes['Notes/Former reading page.md'],'former-reading-page');
  assert.match(await f.exported(first,`preview/obsidian/${config.id}/Notes/Former reading page.md`),/Current vault content/);
  assert.equal(await f.exported(first,`preview/obsidian/${config.id}/Notes/Analysis.ipynb`),'{"cells":[],"nbformat":4}');
  await f.put('Notes/Former reading page.md','Updated vault content.');
  const next=await f.run();
  assert.notEqual(next.revision,first.revision);
  assert.match(await f.exported(next,`preview/obsidian/${config.id}/Notes/Former reading page.md`),/Updated vault content/);
});


test('gallery blocks preserve ordered originals, captions and publication selection', async () => {
  const f = await fixture();
  const portrait = await sharp({ create: { width: 40, height: 20, channels: 3, background: 'red' } }).jpeg().withMetadata({ orientation: 6 }).toBuffer();
  const second = await sharp({ create: { width: 15, height: 35, channels: 3, background: 'blue' } }).png().toBuffer();
  await f.put('Assets/portrait.jpg', portrait);
  await f.put('Assets/second.png', second);
  const body = '---\n[[Assets/portrait.jpg|Red portrait]]\nFirst line.\n\n<script>literal caption</script>\n---\n---\n[[Assets/second.png]]\n---\n';
  await f.put('Blog/creativity/photography/article.md', f.note(body, { kind: 'gallery' }));
  const preview = await f.run();
  const directory = 'interests/creativity/photography/article';
  const metadata = JSON.parse(await f.exported(preview, `preview/${directory}/gallery.json`));
  const names = Object.keys(metadata.images);
  assert.equal(names.length, 2);
  assert.equal(metadata.images[names[0]].caption, 'First line.\n\n<script>literal caption</script>');
  assert.equal(metadata.images[names[1]].caption, undefined);
  assert.equal(metadata.images[names[0]].alt, 'Red portrait');
  for (const [index, bytes] of [portrait, second].entries())
    assert.deepEqual(await readFile(path.join(f.output, preview.revision, `preview/${directory}/${names[index]}`)), bytes);
  await assert.rejects(f.exported(preview, `published/${directory}/gallery.json`), { code: 'ENOENT' });
  await f.put('Blog/creativity/photography/article.md', f.note(body, { kind: 'gallery', status: 'published' }));
  const published = await f.run();
  assert.equal(JSON.parse(await f.exported(published, `published/${directory}/gallery.json`)).draft, false);
  await f.put('Blog/creativity/photography/article.md', f.note('---\n[[Missing.jpg]]\n---', { kind: 'gallery' }));
  await assert.rejects(f.run(), /Missing reference/);
  assert.equal(JSON.parse(await readFile(path.join(f.output, 'current.json'))).revision, published.revision);
});

test('ordinary and cover images retain original bytes and EXIF orientation', async () => {
  const f = await fixture();
  const bytes = await sharp({ create: { width: 31, height: 19, channels: 3, background: 'green' } }).jpeg().withMetadata({ orientation: 8 }).toBuffer();
  await f.put('Assets/portrait.jpg', bytes);
  await f.put('Blog/creativity/photography/article.md', f.note('![[Assets/portrait.jpg]]', { 'cover-media': '[[Assets/portrait.jpg]]', 'cover-alt': 'Green portrait' }));
  const result = await f.run();
  const checksums = JSON.parse(await f.exported(result, 'checksums.json'));
  const image = Object.keys(checksums).find(name => name.endsWith('.jpg'));
  assert.ok(image);
  assert.deepEqual(await readFile(path.join(f.output, result.revision, image)), bytes);
});

test('warm export reads only changed dependencies and draft removes published output', async () => {
  const f = await fixture();
  await f.put('Blog/creativity/photography/_index.md', '---\nid: 808540ac-45c8-4183-8627-dcecdbef1fac\nview: list\n---\n');
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source]]', { status: 'published' }));
  const first = await f.run();
  assert.ok(first.sourceReadBytes > 0);
  const warm = await f.run();
  assert.equal(warm.sourceReadBytes, 0);
  const replacement = 'Updated embedded source.';
  await f.put('Notes/Source.md', replacement);
  const changed = await f.run();
  assert.equal(changed.sourceReadBytes, Buffer.byteLength(replacement));
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source]]'));
  const draft = await f.run();
  assert.match(await f.exported(draft), /Updated embedded source/);
  await assert.rejects(f.exported(draft, 'published/interests/creativity/photography/article.md'), { code: 'ENOENT' });
});

test('index deltas resolve added embeds and remove deleted articles without a vault rescan', async () => {
  const f = await fixture();
  await f.run();
  await f.put('Notes/New.md', 'New source via index event.');
  await f.put('Blog/creativity/photography/article.md', f.note('![[New]]'));
  const changed = await f.run(['Notes/New.md', 'Blog/creativity/photography/article.md']);
  assert.match(await f.exported(changed), /New source via index event/);
  await rm(path.join(f.vault, 'Blog/creativity/photography/article.md'));
  const deleted = await f.run(['Blog/creativity/photography/article.md']);
  assert.deepEqual(JSON.parse(await f.exported(deleted, 'manifest.json')), []);
});

test('unchanged maps reuse their graph, while changed and newly available notes invalidate it', async () => {
  const f = await fixture();
  const scene = { type: 'excalidraw', version: 2, elements: [{ id: 'card', type: 'embeddable', link: '[[Source]]', x: 0, y: 0, width: 400, height: 300 }], appState: {}, files: {} };
  await f.put('Map.md', '---\nexcalidraw-plugin: parsed\n---\n```json\n' + JSON.stringify(scene) + '\n```');
  await f.put('Blog/creativity/photography/article.md', f.note('![[Map]]'));
  await f.run();
  await f.put('Blog/creativity/photography/another.md', f.note('Independent article.', { id: 'another' }));
  const reused = await f.run(['Blog/creativity/photography/another.md']);
  assert.equal(reused.reusedMaps, 1);
  const config = JSON.parse(await f.exported(reused, 'preview/obsidian/collections.json'))[0];
  assert.match(await f.exported(reused, 'preview/obsidian/' + config.id + '/Notes/Source.md'), /Original body/);
  await f.put('Notes/Source.md', 'Changed source in cached map. [[Missing]]');
  const updated = await f.run(['Notes/Source.md']);
  assert.equal(updated.reusedMaps, 0);
  assert.match(await f.exported(updated, 'preview/obsidian/' + config.id + '/Notes/Source.md'), /Changed source/);
  await f.put('Notes/Missing.md', 'Now available.');
  const available = await f.run(['Notes/Missing.md']);
  assert.equal(available.reusedMaps, 0);
  assert.match(await f.exported(available, 'preview/obsidian/' + config.id + '/Notes/Missing.md'), /Now available/);
});

test('folder notes own page bodies and galleries without submenus; Waypoint stays private', async () => {
  const f = await fixture();
  await f.put('Assets/photo.png', await sharp({ create: { width: 20, height: 10, channels: 3, background: 'red' } }).png().toBuffer());
  await f.put('Blog/photos/photos.md', f.note('%% Begin Waypoint %%\n- [[Do not resolve this]]\n%% End Waypoint %%\n\n---\n[[Assets/photo.png]]\nA caption\n---', { id: 'photo-folder', kind: 'gallery', title: 'My Photos', order: 42, status: 'draft' }));
  const result = await f.run();
  const gallery = JSON.parse(await f.exported(result, 'preview/interests/photos/gallery.json'));
  assert.equal(gallery.url, '/photos');
  assert.equal(gallery.title, 'My Photos');
  assert.equal(gallery.order, 42);
  assert.match(gallery.lastEditedAt, /^\d{4}-\d{2}-\d{2}$/);
  await assert.rejects(f.exported(result, 'published/interests/photos/gallery.json'), { code: 'ENOENT' });
  const navigation = await f.exported(result, 'published/interests/photos/photos.md');
  assert.doesNotMatch(navigation, /A caption|photo.png|Waypoint/);
});

test('custom titles win, blank titles use exact filenames and URLs remain filename-based', async () => {
  const f = await fixture();
  for (const title of ['Custom punctuation — yes!', '']) {
    await f.put('Blog/creativity/photography/article.md', f.note('Text.', { title, order: 0, lastEditedAt: '2026-10-26' }));
    const result = await f.run();
    const source = await f.exported(result);
    assert.match(source, title ? /title: Custom punctuation — yes!/ : /title: article/);
    assert.match(source, /url: \/creativity\/photography\/article/);
    assert.match(source, /order: 0/);
    assert.match(source, /lastEditedAt: '2026-10-26'/);
  }
});

test('blank folder titles preserve exact names while URLs use hyphens', async () => {
  const f = await fixture();
  await f.put('Blog/my Photos/my Photos.md', f.note('My photos.', { id: 'folder-name', title: '', status: 'published' }));
  const source = await f.exported(await f.run(), 'published/interests/my Photos/my Photos.md');
  assert.match(source, /title: my Photos/);
  assert.match(source, /url: \/my-photos/);
});

test('heading embeds omit the selected heading and retain its subheadings', async () => {
  const f = await fixture();
  await f.put('Notes/Source.md', '# Selected\nBody.\n## Detail\nMore.\n# Other\nPrivate.');
  await f.put('Blog/creativity/photography/article.md', f.note('![[Source#Selected]]'));
  const source = await f.exported(await f.run());
  assert.doesNotMatch(source, /# Selected|Private/);
  assert.match(source, /## Detail/);
  assert.match(source, /Body/);
});
