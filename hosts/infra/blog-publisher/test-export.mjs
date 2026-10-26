import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, readdir, symlink, rename } from 'node:fs/promises';
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
  const run = () => exportVault({ vault, output, quietMs: 0 });
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
test('About folder body is editable, expands notes and keeps vault markup inert', async () => {
  const f = await fixture();
  const about = '---\nid: 7e85bf84-ad34-46c1-a0f2-a3e428bb36ab\ntitle: About\nslug: about\n---\n';
  await f.put('Blog/about/_index.md', about + '![[Source]]\n\n{danger()}\n\n<script>alert(1)</script>');
  const first = await f.run();
  const result = await f.exported(first, 'preview/interests/about/_index.md');
  assert.match(result, /Original body/);
  assert.doesNotMatch(result, /secret|invalid YAML|(?<!\\)<script>|\n\{danger/);
  assert.equal(result, await f.exported(first, 'published/interests/about/_index.md'));
  await f.put('Blog/about/_index.md', about + 'My updated biography.');
  const second = await f.run();
  assert.notEqual(second.revision, first.revision);
  assert.match(await f.exported(second, 'preview/interests/about/_index.md'), /My updated biography/);
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
  assert.equal(Object.keys(sums).filter(p => p.endsWith('.webp')).length, 1);
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
  await f.put('Blog/creativity/photography/article.md', f.note('![[Map]]'));
  const first = await f.run();
  const configs = JSON.parse(await f.exported(first, 'preview/obsidian/collections.json'));
  assert.equal(configs.length, 1);
  assert.deepEqual(JSON.parse(await f.exported(first, 'published/obsidian/collections.json')), []);
  const config = configs[0];
  assert.equal(config.noteRoutes['Notes/one/two/three/four/five/Deep.md'], 'deep');
  assert.match(await f.exported(first, 'preview/interests/creativity/photography/article.mdx'), /<ObsidianMap/);
  assert.doesNotMatch(await f.exported(first, 'preview/obsidian/' + config.id + '/Notes/one/two/three/four/five/Deep.md'), /secret/);
  await f.put('Notes/one/two/three/four/five/Renamed.md', 'Edited and renamed.');
  scene.elements[0].link = '[[Notes/one/two/three/four/five/Renamed]]';
  await f.put('Map.md', drawing());
  const next = await f.run();
  const changed = JSON.parse(await f.exported(next, 'preview/obsidian/collections.json'))[0];
  assert.equal(changed.noteRoutes['Notes/one/two/three/four/five/Renamed.md'], 'deep');
  assert.notEqual(first.revision, next.revision);
  assert.doesNotMatch(await readFile(path.join(f.vault, 'Notes/one/two/three/four/five/Renamed.md'), 'utf8'), /id:/);
});
test('filenames and folder names own labels while explicit ordering and permalink survive renames', async () => {
  const f = await fixture();
  await f.run();
  await rename(path.join(f.vault, 'Blog/creativity/photography/article.md'), path.join(f.vault, 'Blog/creativity/photography/Better name.md'));
  await rename(path.join(f.vault, 'Blog/creativity/photography'), path.join(f.vault, 'Blog/creativity/Pictures'));
  const result = await f.run();
  assert.match(await f.exported(result, 'preview/interests/creativity/Pictures/Better name.md'), /title: Better name/);
  assert.match(await f.exported(result, 'preview/interests/creativity/Pictures/Better name.md'), /url: \/creativity\/photography\/article/);
  assert.match(await f.exported(result, 'preview/interests/creativity/Pictures/_index.md'), /title: Pictures/);
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
