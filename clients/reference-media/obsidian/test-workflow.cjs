const { test } = require('node:test');
const assert = require('node:assert/strict');
const Module = require('node:module');

// Obsidian host seam: the real command, modal and playback handlers run here.
class Element extends EventTarget {
  constructor(tag = 'div', options = {}) { super(); this.tag = tag; this.children = []; this.attributes = { ...options.attr }; this.textContent = options.text || ''; this.value = options.value || ''; this.dataset = {}; this.style = {}; this.isConnected = true; this.nodeType = 1; this.paused = true; this.duration = 20; this.className = options.cls || ''; }
  createEl(tag, options) { const child = new Element(tag, options); child.parent = this; child.parentElement = this; this.children.push(child); return child; }
  createDiv(options) { return this.createEl('div', options); }
  addClass(cls) { this.className += ' ' + cls; }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; if (key === 'src') this.src = ''; }
  empty() { for (const child of this.children) child.isConnected = false; this.children = []; }
  remove() { this.isConnected = false; this.parent.children = this.parent.children.filter(c => c !== this); }
  querySelectorAll(selector) { return this.children.flatMap(c => [...(selector.split(',').includes(c.tag) ? [c] : []), ...c.querySelectorAll(selector)]); }
  getRootNode() { return { nodeType: 9 }; }
  pause() { this.paused = true; }
  play() { this.paused = false; this.dispatchEvent(new Event('play')); return Promise.resolve(); }
  load() { this.loaded = true; }
  focus() {}
  setPointerCapture() {}
  releasePointerCapture() {}
  getBoundingClientRect() { const top = (this.parent?.children.indexOf(this) || 0) * 40; return { top, bottom: top + 40 }; }
}
let opened;
class Modal {
  constructor(app) { this.app = app; this.contentEl = new Element(); this.modalEl = new Element(); }
  open() { opened = this; this.onOpen?.(); }
  close() { this.onClose?.(); }
}
class Plugin { registerDomEvent(target, type, handler) { target.addEventListener(type, handler); } }
const original = Module._load;
Module._load = function(name, ...args) {
  if (name === 'obsidian') return { Plugin, Modal, FuzzySuggestModal: class extends Modal {}, Notice: class {}, Platform: { resourcePathPrefix: 'app://local/' }, PluginSettingTab: class {}, Setting: class {}, setIcon: () => {} };
  return original.call(this, name, ...args);
};
const ReferenceBoards = require('./main.js');
Module._load = original;
const asset = (n, key, ordinal = 0) => ({ id: String(n).repeat(64), path: `objects/${String(n).repeat(64)}.mp4`, thumbnail: `References/Thumbnails/${String(n).repeat(64)}.jpg`, origins: [{ source_key: key, ordinal }] });
const findButton = (modal, text) => modal.contentEl.querySelectorAll('button').find(b => b.textContent.includes(text) || b.attributes['aria-label']?.includes(text));
test('Add reference browses exact collection before selection with thumbnails and coordinated seekable previews', async () => {
  const catalog = { collections: [{ source: 'instagram', id: 'g', title: 'Grind', active: 1 }],
    items: ['A', 'B', 'Samurai', 'Pending'].map(id => ({ source: 'instagram', id, source_key: 'instagram:' + id, metadata: { title: id } })),
    memberships: ['A', 'B', 'Pending'].map((id, ordinal) => ({ source: 'instagram', collection_id: 'g', item_id: id, ordinal, active: 1 })),
    assets: [asset(1, 'instagram:A'), asset(2, 'instagram:A', 1), asset(3, 'instagram:B'), asset(4, 'instagram:Samurai')] };
  const plugin = new ReferenceBoards();
  plugin.settings = { catalog: 'References/Catalog.json', archiveRoot: '/Volumes/Media/references' };
  plugin.app = { vault: { adapter: { read: async () => JSON.stringify(catalog), getResourcePath: p => 'vault://' + p } } };
  plugin.players = new Set(); plugin.allowedPlayers = new WeakSet(); plugin.board = () => ({ path: 'Board.excalidraw.md' });
  await plugin.addReference();
  findButton(opened, 'Instagram').onclick(); findButton(opened, 'Grind').onclick();
  assert.match(opened.summary.textContent, /3 of 3 current posts/);
  assert.equal(findButton(opened, 'Samurai'), undefined);
  assert.equal(opened.grid.children.length, 3);
  assert.match(opened.grid.querySelectorAll('img')[0].src, /^vault:\/\/References\/Thumbnails\//);
  findButton(opened, 'Preview A').onclick();
  const first = opened.preview;
  assert.equal(first.paused, true); assert.equal(first.controls, true); assert.equal(first.preload, 'metadata');
  assert.match(first.src, /objects\/.+\.mp4\?\d+$/);
  assert.match(plugin.fileURL(catalog.assets[0]), /^file:\/\/\/Volumes\/Media\/references\/objects\/.+\.mp4$/);
  first.currentTime = 8; first.dispatchEvent(new Event('loadedmetadata'));
  assert.equal(first.currentTime, 8);
  first.play(); assert.equal(first.paused, true, 'unsolicited playback is blocked');
  findButton(opened, 'Play preview').onclick(); assert.equal(first.paused, false);
  findButton(opened, 'Preview member 2').onclick();
  assert.equal(first.paused, true); assert.equal(first.src, '');
  const second = opened.preview; second.dispatchEvent(new Event('pointerdown')); second.play();
  const boardPlayer = new Element('video'); plugin.watchPlayer(boardPlayer); boardPlayer.dispatchEvent(new Event('pointerdown')); boardPlayer.play();
  assert.equal(second.paused, true, 'board playback stops picker playback');
  second.dispatchEvent(new Event('pointerdown')); second.play(); assert.equal(boardPlayer.paused, true);
  findButton(opened, 'Preview B').onclick(); assert.equal(second.paused, true);
  opened.preview.dispatchEvent(new Event('error'));
  assert.ok(opened.detail.querySelectorAll('p').some(p => /Archive offline/.test(p.textContent)));
  assert.equal(findButton(opened, 'Choose full video').disabled, true);
  const last = opened.preview; opened.close(); assert.equal(last.paused, true); assert.equal(last.src, '');
});

const { MODEL, DEFAULTS } = require('./context.cjs');
const ready = id => ({ asset_id: id, model: MODEL, status: 'ready', result: { duration: 20, quality_warnings: ['Check names'], segments: [{ start: 3, end: 8, text: `Evidence ${id[0]}` }] } });
const flush = () => new Promise(resolve => setImmediate(resolve));
const checkbox = (modal, id) => modal.detail.querySelectorAll('input').find(e => e.dataset.asset === id);
const check = (modal, id, value = true) => { const c = checkbox(modal, id); c.checked = value; c.onchange(); };
async function contextFixture(request = async h => h.asset_ids.map(ready)) {
  const catalog = {
    collections: [
      { source: 'instagram', id: 'g', title: 'Grind', active: 1 },
      { source: 'yaay', id: 'travel', title: 'Travel', active: 1 },
      { source: 'yaay', id: 'child', title: 'Child', parent: 'travel', active: 1 },
      { source: 'yaay', id: 'deep', title: 'Deep', parent: 'child', active: 1 },
    ],
    items: ['A', 'B'].map(id => ({ source: 'instagram', id, source_key: 'instagram:' + id, metadata: { title: id } })).concat([{ source: 'yaay', id: 'alias', source_key: 'instagram:A', metadata: { title: 'A alias' } }]),
    memberships: [
      ...['A', 'B'].map((id, ordinal) => ({ source: 'instagram', collection_id: 'g', item_id: id, ordinal, active: 1 })),
      { source: 'yaay', collection_id: 'child', item_id: 'alias', ordinal: 0, active: 1 },
    ],
    assets: [asset(1, 'instagram:A'), asset(2, 'instagram:A', 1), { ...asset(3, 'instagram:A', 2), path: `objects/${'3'.repeat(64)}.jpg` }, asset(4, 'instagram:B')],
  };
  const plugin = new ReferenceBoards(), files = [], calls = [];
  plugin.settings = { ...DEFAULTS, catalog: 'References/Catalog.json', archiveRoot: '/Volumes/Media/references' };
  plugin.app = { vault: {
    adapter: { read: async () => JSON.stringify(catalog), getResourcePath: p => 'vault://' + p },
    getAbstractFileByPath: () => true, createBinary: async (path, content) => files.push({ path, content }), create: async (path, content) => { const file = { path, content }; files.push(file); return file; },
  }, workspace: { getLeaf: () => ({ openFile: async () => {} }) } };
  plugin.players = new Set(); plugin.allowedPlayers = new WeakSet();
  plugin.archiveRequest = async header => { calls.push(header); return request(header); };
  await plugin.createBrief();
  const modal = opened;
  findButton(modal, 'Instagram').onclick(); findButton(modal, 'Grind').onclick();
  return { modal, plugin, files, calls, catalog };
}
test('shared context browser keeps preview, native checkboxes, carousel IDs and ordered selection independent', async () => {
  const { modal, calls } = await contextFixture();
  assert.equal(modal.grid.children.length, 2, 'one card per post');
  assert.equal(modal.grid.querySelectorAll('input').length, 0, 'browse cards have no member lists');
  findButton(modal, 'Preview A').onclick(); const preview = modal.preview;
  check(modal, '2'.repeat(64)); check(modal, '1'.repeat(64));
  assert.equal(modal.detail.querySelectorAll('input').length, 2, 'images have no checkbox');
  assert.equal(modal.preview, preview); assert.equal(preview.paused, true);
  assert.deepEqual([...modal.selected.keys()], ['2'.repeat(64), '1'.repeat(64)]);
  findButton(modal, 'Preview B').onclick();
  assert.deepEqual([...modal.selected.keys()], ['2'.repeat(64), '1'.repeat(64)]);
  assert.equal(checkbox(modal, '4'.repeat(64)).checked, false);
  assert.equal(findButton(modal, 'Preview B').attributes['aria-pressed'], 'true');
  assert.equal(findButton(modal, 'Preview A').attributes['aria-pressed'], 'false');
  await flush();
  assert.ok(calls.every(h => h.action === 'transcripts'), 'preview and checking never queue transcription');
  assert.match(modal.selectionSummary.textContent, /2 ready/);
});
test('selection and task survive search, ordering, parent navigation and cross-source membership', async () => {
  const { modal } = await contextFixture();
  findButton(modal, 'Preview A').onclick(); check(modal, '2'.repeat(64));
  findButton(modal, 'Preview B').onclick(); check(modal, '4'.repeat(64));
  const retainedPreview = modal.preview;
  const task = modal.contentEl.querySelectorAll('textarea')[0]; task.value = 'Compare workflows'; task.oninput();
  const search = modal.page.querySelectorAll('input').find(e => e.attributes['aria-label'] === 'Search within this collection');
  search.value = 'B'; search.oninput(); assert.equal(modal.grid.children.length, 1);
  const order = modal.page.querySelectorAll('select')[0]; order.value = 'newest'; order.onchange();
  findButton(modal, 'Sources').onclick(); findButton(modal, 'Yaay').onclick();
  assert.equal(findButton(modal, 'Child'), undefined); assert.equal(findButton(modal, 'Deep'), undefined);
  findButton(modal, 'Travel').onclick(); assert.ok(findButton(modal, 'Child')); assert.equal(findButton(modal, 'Deep'), undefined);
  findButton(modal, 'Child').onclick(); assert.ok(findButton(modal, 'Deep'));
  assert.equal(modal.preview, retainedPreview, 'preview survives navigation');
  findButton(modal, 'Preview A').onclick();
  assert.equal(checkbox(modal, '2'.repeat(64)).checked, true);
  check(modal, '2'.repeat(64)); assert.equal(modal.selected.size, 2, 'alias does not duplicate ID');
  findButton(modal, 'Back').onclick(); assert.equal(modal.collection.id, 'travel');
  assert.equal(task.value, 'Compare workflows'); assert.equal(modal.task, task.value);
  assert.deepEqual([...modal.selected.keys()], ['2'.repeat(64), '4'.repeat(64)]);
  findButton(modal, 'Remove A').onclick(); assert.deepEqual([...modal.selected.keys()], ['4'.repeat(64)]);
  modal.clear.onclick(); assert.equal(modal.selected.size, 0);
});
test('cached transcripts follow the previewed carousel member and stale results never replace it', async () => {
  const resolve = new Map();
  const { modal } = await contextFixture(h => new Promise(done => resolve.set(h.asset_ids[0], done)));
  findButton(modal, 'Preview A').onclick(); const firstPanel = modal.transcriptPanel;
  assert.match(firstPanel.querySelectorAll('p')[0].textContent, /Loading/);
  findButton(modal, 'Preview member 2').onclick(); const panel = modal.transcriptPanel;
  resolve.get('2'.repeat(64))([ready('2'.repeat(64))]); await flush();
  assert.equal(panel.querySelectorAll('span')[0].textContent, 'Evidence 2');
  resolve.get('1'.repeat(64))([ready('1'.repeat(64))]); await flush();
  assert.equal(modal.transcriptPanel, panel); assert.equal(panel.querySelectorAll('span')[0].textContent, 'Evidence 2');
  assert.equal(firstPanel.querySelectorAll('span').length, 0, 'stale detached pane is not rendered');
  assert.ok(panel.querySelectorAll('p').some(p => /Check names/.test(p.textContent)));
  const player = modal.preview; findButton(modal, 'Seek to 0:03.0').onclick();
  assert.equal(player.currentTime, 3); assert.equal(player.paused, true, 'seeking does not start playback');
  findButton(modal, 'Preview B').onclick(); const last = modal.transcriptPanel;
  modal.close(); resolve.get('4'.repeat(64))([ready('4'.repeat(64))]); await flush();
  assert.equal(last.querySelectorAll('span').length, 0, 'closing invalidates pending transcript render');
});
test('transcript errors, pending and unavailable states do not prevent video playback', async () => {
  const { modal } = await contextFixture(async h => {
    const id = h.asset_ids[0];
    if (id[0] === '1') throw new Error('Offline');
    return [{ asset_id: id, model: MODEL, status: id[0] === '2' ? 'pending' : 'unavailable' }];
  });
  findButton(modal, 'Preview A').onclick(); await flush();
  assert.ok(modal.transcriptPanel.querySelectorAll('p').some(p => /Video playback is independent/.test(p.textContent)));
  findButton(modal, 'Play preview').onclick(); assert.equal(modal.preview.paused, false);
  findButton(modal, 'Preview member 2').onclick(); await flush();
  assert.ok(modal.transcriptPanel.querySelectorAll('p').some(p => /pending on the server/.test(p.textContent)));
  findButton(modal, 'Preview B').onclick(); await flush();
  assert.ok(modal.transcriptPanel.querySelectorAll('p').some(p => /Transcript unavailable/.test(p.textContent)));
});
test('cached selection exports exact ordered videos without requesting transcription or needing a board', async () => {
  const { modal, files, calls } = await contextFixture();
  modal.task = 'Compare workflows';
  findButton(modal, 'Preview B').onclick(); check(modal, '4'.repeat(64));
  findButton(modal, 'Preview A').onclick(); check(modal, '2'.repeat(64));
  findButton(modal, 'Preview A').onclick(); await flush();
  await modal.save.onclick();
  assert.equal(files.length, 2);
  const manifest = JSON.parse(files.find(f => f.path.endsWith('.json')).content);
  assert.deepEqual(manifest.evidence.map(e => e.asset_id), ['4'.repeat(64), '2'.repeat(64)]);
  assert.equal(manifest.task, 'Compare workflows');
  assert.ok(calls.every(h => h.action === 'transcripts'));
});
test('missing selected evidence blocks export; explicit request refreshes exactly the selection', async () => {
  let requested = false;
  const { modal, calls, files } = await contextFixture(async h => {
    if (h.action === 'request_transcripts') requested = true;
    return h.asset_ids.map(id => requested ? ready(id) : { asset_id: id, model: MODEL, status: 'pending' });
  });
  modal.task = 'Compare'; findButton(modal, 'Preview A').onclick(); check(modal, '2'.repeat(64)); await flush();
  await modal.save.onclick(); assert.equal(files.length, 0); assert.match(modal.selectionSummary.textContent, /still need transcripts/);
  await modal.request.onclick();
  assert.deepEqual(calls.find(h => h.action === 'request_transcripts').asset_ids, ['2'.repeat(64)]);
  await modal.save.onclick(); assert.equal(files.length, 2);
});
test('selection limit rejects a 51st ID without affecting preview or existing selection', async () => {
  const { modal } = await contextFixture();
  findButton(modal, 'Preview A').onclick(); const preview = modal.preview;
  for (let i = 0; i < 50; i++) modal.selected.set(i.toString(16).padStart(64, '0'), { id: i.toString(16).padStart(64, '0'), title: `Test ${i}`, ordinal: 0 });
  check(modal, '2'.repeat(64));
  assert.equal(modal.selected.size, 50); assert.equal(checkbox(modal, '2'.repeat(64)).checked, false);
  assert.equal(modal.preview, preview);
});

test('drag handles and keyboard reorder the bottom list; clipboard and saved evidence use that order', async () => {
  const { modal, plugin, files } = await contextFixture();
  const copied = []; plugin.copyText = async text => copied.push(text);
  findButton(modal, 'Preview A').onclick(); check(modal, '1'.repeat(64)); check(modal, '2'.repeat(64));
  findButton(modal, 'Preview B').onclick(); check(modal, '4'.repeat(64)); await flush();
  const handle = () => modal.selectedList.querySelectorAll('button').find(b => b.dataset.handle === '4'.repeat(64));
  const drag = { preventDefault() {}, button: 0, pointerId: 1, clientY: 20 };
  handle().onpointerdown(drag); handle().onpointermove(drag); handle().onpointerup(drag);
  assert.deepEqual([...modal.selected.keys()], ['4'.repeat(64), '1'.repeat(64), '2'.repeat(64)]);
  handle().onkeydown({ key: 'ArrowDown', preventDefault() {} });
  assert.deepEqual([...modal.selected.keys()], ['1'.repeat(64), '4'.repeat(64), '2'.repeat(64)]);
  const preview = modal.preview;
  await modal.copyText.onclick();
  assert.equal(modal.preview, preview); assert.equal(modal.closed, false); assert.equal(files.length, 0);
  assert.match(copied[0], /Episode 1: A[\s\S]*Episode 2: B[\s\S]*Episode 3: A/);
  assert.match(copied[0], /Transcription warning: Check names/);
  await modal.save.onclick();
  assert.deepEqual(JSON.parse(files.find(f => f.path.endsWith('.json')).content).evidence.map(e => e.asset_id), [...modal.selected.keys()]);
});

test('capture, remove, copy and save only chosen frames, matched to reordered episode and timestamp', async () => {
  const { modal, plugin, files } = await contextFixture();
  const sheets = [], images = []; let text;
  plugin.captureCanvas = video => ({ width: 300, height: 200, toDataURL: () => 'data:image/png;fixture' });
  plugin.frameSheet = async frames => { sheets.push(frames.map(f => ({ asset_id: f.asset_id, episode: f.episode, seconds: f.seconds }))); return new Blob(['png'], { type: 'image/png' }); };
  plugin.copyImage = async blob => images.push(blob); plugin.copyText = async value => text = value;
  findButton(modal, 'Preview A').onclick(); check(modal, '1'.repeat(64));
  modal.preview.currentTime = 8; await modal.captureButton.onclick();
  modal.preview.currentTime = 3; await modal.captureButton.onclick(); await modal.captureButton.onclick();
  assert.equal(modal.frames.length, 2, 'duplicate frame is rejected');
  findButton(modal, 'Preview B').onclick(); check(modal, '4'.repeat(64));
  modal.preview.currentTime = 5; await modal.captureButton.onclick();
  modal.reorder('4'.repeat(64), 0); await flush();
  await modal.copyImages.onclick();
  assert.deepEqual(sheets[0].map(f => [f.episode, f.seconds]), [[1, 5], [2, 3], [2, 8]]);
  assert.equal(images[0].type, 'image/png'); assert.equal(files.length, 0);
  await modal.copyText.onclick(); assert.match(text, /Chosen frames: \[0:03.0\], \[0:08.0\]/);
  findButton(modal, 'Preview selected A').onclick();
  findButton(modal, 'Remove 0:03.0').onclick(); assert.equal(modal.frames.length, 2);
  await modal.save.onclick();
  const manifest = JSON.parse(files.find(f => f.path.endsWith('.json')).content);
  assert.deepEqual(manifest.frames.map(f => [f.episode, f.seconds]), [[1, 5], [2, 8]]);
  assert.ok(files.some(f => f.path === manifest.image_sheet));
  assert.ok(files.find(f => f.path.endsWith('.md')).content.includes(manifest.image_sheet));
});

test('clipboard errors and incomplete transcripts retain selection; image export does not pretend to include uncaptured videos', async () => {
  const { modal, plugin, files } = await contextFixture(async h => h.asset_ids.map(id => ({ asset_id: id, model: MODEL, status: 'pending' })));
  let copies = 0; plugin.copyText = async () => { copies++; throw new Error('Clipboard denied'); };
  findButton(modal, 'Preview A').onclick(); check(modal, '1'.repeat(64)); await flush();
  await modal.copyText.onclick(); assert.equal(copies, 0); assert.match(modal.selectionSummary.textContent, /still need transcripts/);
  await modal.copyImages.onclick(); assert.match(modal.selectionSummary.textContent, /capture a frame/);
  modal.receipts.set('1'.repeat(64), ready('1'.repeat(64)));
  await modal.copyText.onclick(); assert.match(modal.selectionSummary.textContent, /Clipboard denied/);
  assert.equal(modal.selected.size, 1); assert.equal(modal.copyText.disabled, false); assert.equal(files.length, 0);
  modal.frames.push({ asset_id: '1'.repeat(64), seconds: 1 });
  findButton(modal, 'Remove A').onclick(); assert.equal(modal.frames.length, 0);
});

test('frame capture decodes an initially transparent video frame without playback and rejects blank results', async () => {
  const oldDocument = global.document;
  const video = new Element('video'); Object.assign(video, { readyState: 2, videoWidth: 1080, videoHeight: 1920 });
  let seconds = 0, alpha = 0;
  Object.defineProperty(video, 'currentTime', { get: () => seconds, set: value => {
    seconds = value; queueMicrotask(() => { alpha = 255; video.dispatchEvent(new Event('seeked')); });
  } });
  const ctx = { drawImage() {}, getImageData: () => ({ data: [0, 0, 0, alpha] }) };
  global.document = { createElement: () => ({ getContext: () => ctx }) };
  try {
    const canvas = await new ReferenceBoards().captureCanvas(video);
    assert.equal(canvas.height, 1280); assert.equal(video.paused, true); assert.equal(seconds, 0.001);
    ctx.getImageData = () => ({ data: [0, 0, 0, 0] });
    await assert.rejects(new ReferenceBoards().captureCanvas(video), /Frame not decoded/);
    video.seeking = true;
    await assert.rejects(new ReferenceBoards().captureCanvas(video), /Wait for the video frame/);
  } finally { global.document = oldDocument; }
});
