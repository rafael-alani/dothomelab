const { test } = require('node:test');
const assert = require('node:assert/strict');
const Module = require('node:module');

// Obsidian host seam: the real command, modal and playback handlers run here.
class Element extends EventTarget {
  constructor(tag = 'div', options = {}) { super(); this.tag = tag; this.children = []; this.attributes = { ...options.attr }; this.textContent = options.text || ''; this.value = options.value || ''; this.dataset = {}; this.style = {}; this.isConnected = true; this.nodeType = 1; this.paused = true; this.duration = 20; this.className = options.cls || ''; }
  createEl(tag, options) { const child = new Element(tag, options); child.parent = this; this.children.push(child); return child; }
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
  if (name === 'obsidian') return { Plugin, Modal, FuzzySuggestModal: class extends Modal {}, Notice: class {}, Platform: { resourcePathPrefix: 'app://local/' }, PluginSettingTab: class {}, Setting: class {} };
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
  assert.match(first.src, /objects\/.+\.mp4$/);
  first.currentTime = 8; first.dispatchEvent(new Event('loadedmetadata'));
  assert.equal(first.currentTime, 8);
  first.play(); assert.equal(first.paused, true, 'unsolicited playback is blocked');
  first.dispatchEvent(new Event('pointerdown')); first.play(); assert.equal(first.paused, false);
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
