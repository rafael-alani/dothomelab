const { Plugin, Modal, FuzzySuggestModal, Notice, Platform, PluginSettingTab, Setting } = require('obsidian');
const path = require('path');
const { pathToFileURL } = require('url');
const { validateAsset, range, readCard, playerBlock, replacePlayer, library, browse, collectionLabel } = require('./model.cjs');

class Picker extends FuzzySuggestModal {
  constructor(app, items, choose, prompt) { super(app); this.items = items; this.choose = choose; this.setPlaceholder(prompt); }
  getItems() { return this.items; }
  getItemText(item) { return item.label || item.title || item.path; }
  onChooseItem(item) { this.choose(item); }
}

const ACQUISITION = { archived: 'Archived', pending: 'Awaiting acquisition', retry: 'Unavailable · retry scheduled', partial: 'Partially archived', unverified: 'Media available · completion unverified' };

class CollectionBrowser extends Modal {
  constructor(plugin, board, catalog) {
    super(plugin.app);
    this.plugin = plugin; this.board = board; this.lib = library(catalog);
    this.search = ''; this.order = 'source'; this.history = false;
  }
  onOpen() { this.modalEl.addClass('reference-browser'); this.showSources(); }
  stopPreview() {
    if (this.preview?.pause) this.preview.pause();
    if (this.preview) {
      this.preview.removeAttribute('src');
      if (this.preview.load) this.preview.load();
      this.plugin.players.delete(this.preview);
    }
    this.preview = null;
  }
  onClose() { this.stopPreview(); this.contentEl.empty(); }
  heading(title, back, action) {
    this.stopPreview(); this.contentEl.empty();
    if (back) this.contentEl.createEl('button', { text: back }).onclick = action;
    this.contentEl.createEl('h2', { text: title });
  }
  showSources() {
    this.heading('Add a reference');
    this.contentEl.createEl('p', { text: 'Choose a source, then a collection. Preview before adding to your board.' });
    const sources = [...new Set([...this.lib.collections.values()].map(c => c.source))];
    for (const source of sources) {
      const button = this.contentEl.createEl('button', { cls: 'reference-collection', text: source[0].toUpperCase() + source.slice(1) });
      button.onclick = () => { this.source = source; this.showCollections(); };
    }
    if (!sources.length) this.contentEl.createEl('p', { text: 'Collection metadata is not available. Run the desktop collector to refresh this older catalog. Existing board cards still work.' });
  }
  showCollections() {
    this.heading('Choose a collection', 'Sources', () => this.showSources());
    const filter = this.contentEl.createEl('input', { type: 'search', placeholder: 'Find a collection', attr: { 'aria-label': 'Find a collection' } });
    const list = this.contentEl.createDiv({ cls: 'reference-collections' });
    const render = () => {
      list.empty();
      const rows = [...this.lib.collections.values()].filter(c => c.source === this.source);
      rows.sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0));
      const visit = (parent, depth, seen = new Set()) => {
        for (const c of rows.filter(c => (c.parent ?? null) === parent && !seen.has(c.id))) {
          seen.add(c.id);
          const label = collectionLabel(this.lib, c.source, c.id);
          if (label.toLocaleLowerCase().includes(filter.value.toLocaleLowerCase())) {
            const count = browse(this.lib, c.source, c.id).length;
            const button = list.createEl('button', { cls: 'reference-collection', text: `${label} · ${count} posts${c.active ? '' : ' · removed collection'}` });
            button.style.paddingInlineStart = `${12 + depth * 16}px`;
            button.onclick = () => { this.collection = c; this.search = ''; this.history = !c.active; this.showCollection(); };
          }
          visit(c.id, depth + 1, seen);
        }
      };
      visit(null, 0);
      if (!list.children.length) list.createEl('p', { text: 'No matching collections.' });
    };
    filter.oninput = render; render(); filter.focus();
  }
  thumbnail(parent, asset, alt) {
    const placeholder = parent.createDiv({ cls: 'reference-thumb-placeholder', text: asset ? 'Thumbnail unavailable' : 'Awaiting media' });
    if (!asset?.thumbnail || !(asset.thumbnail === `References/Thumbnails/${asset.id}.jpg` || /^References\/Thumbnails\/post-[a-f0-9]{24}\.jpg$/.test(asset.thumbnail))) return;
    const image = parent.createEl('img', { cls: 'reference-thumbnail', attr: { alt } });
    image.src = this.app.vault.adapter.getResourcePath(asset.thumbnail);
    image.onload = () => placeholder.remove();
    image.onerror = () => image.remove();
  }
  showCollection() {
    this.heading(collectionLabel(this.lib, this.source, this.collection.id), 'Collections', () => this.showCollections());
    const source = Array.isArray(this.lib.sources) && this.lib.sources.find(s => s.source === this.source);
    const stamp = source?.received ? new Date(source.received * 1000).toLocaleString() : 'unknown';
    this.contentEl.createEl('p', { cls: 'reference-status', text: `Inventory: ${source?.status || 'unknown'} · ${stamp}. Scan completion does not certify source-count parity.` });
    if (this.collection.audit) {
      const audit = this.collection.audit;
      this.contentEl.createEl('p', { cls: 'reference-status', text: `Source grid: ${audit.ui_posts} posts · checked ${new Date(audit.checked_at * 1000).toLocaleString()}${audit.api_only?.length ? ' · API/grid mismatch; historical membership retained' : ''}` });
    }
    const controls = this.contentEl.createDiv({ cls: 'reference-browser-controls' });
    const search = controls.createEl('input', { type: 'search', placeholder: 'Search within this collection', attr: { 'aria-label': 'Search within this collection' } });
    search.value = this.search;
    const order = controls.createEl('select', { attr: { 'aria-label': 'Post order' } });
    for (const [value, text] of [['source', 'Source collection order'], ['newest', 'Published: newest first'], ['oldest', 'Published: oldest first']]) order.createEl('option', { value, text });
    order.value = this.order;
    const history = controls.createEl('select', { attr: { 'aria-label': 'Membership status' } });
    for (const [value, text] of [['current', 'Current contents'], ['removed', 'Removed memberships']]) history.createEl('option', { value, text });
    history.value = this.history ? 'removed' : 'current';
    this.summary = this.contentEl.createEl('p', { cls: 'reference-status', attr: { 'aria-live': 'polite' } });
    const body = this.contentEl.createDiv({ cls: 'reference-browser-body' });
    this.grid = body.createDiv({ cls: 'reference-posts', attr: { 'aria-label': 'Collection posts' } });
    this.detail = body.createDiv({ cls: 'reference-detail', attr: { 'aria-label': 'Post preview' } });
    const refresh = () => { this.search = search.value; this.order = order.value; this.history = history.value === 'removed'; this.renderPosts(); };
    search.oninput = refresh; order.onchange = refresh; history.onchange = refresh;
    this.renderPosts(); search.focus();
  }
  renderPosts() {
    this.stopPreview(); this.grid.empty(); this.detail.empty();
    const all = browse(this.lib, this.source, this.collection.id, { history: this.history });
    const posts = browse(this.lib, this.source, this.collection.id, this);
    const ready = all.filter(p => p.assets.length).length;
    this.summary.textContent = `${posts.length} of ${all.length} ${this.history ? 'removed' : 'current'} posts · ${ready} with media · ${all.length - ready} awaiting media. ${this.order === 'source' ? 'Source order is collection position, not publication date.' : 'Unknown publication dates appear last.'}`;
    for (const post of posts) {
      const button = this.grid.createEl('button', { cls: 'reference-post', attr: { 'aria-label': `Preview ${post.title}`, 'aria-pressed': 'false' } });
      this.thumbnail(button, post.assets.find(a => a.thumbnail) || (post.thumbnail ? { thumbnail: post.thumbnail } : null), post.title);
      button.createEl('span', { cls: 'reference-post-title', text: post.title });
      const videoCount = post.assets.filter(a => /\.(mp4|webm|mov)$/.test(a.path)).length;
      button.createEl('span', { cls: 'reference-post-meta', text: `${post.assets.length} media${videoCount ? ` · ${videoCount} video` : ''} · ${ACQUISITION[post.status] || post.status}` });
      button.onclick = () => {
        for (const other of this.grid.querySelectorAll('button')) other.setAttribute('aria-pressed', String(other === button));
        this.showPost(post);
      };
    }
    this.detail.createEl('p', { text: posts.length ? 'Select a post to preview its media. Videos start paused.' : 'No posts match this collection and search. Removed memberships are available separately.' });
  }
  showPost(post) {
    this.stopPreview(); this.detail.empty();
    this.detail.createEl('h3', { text: post.title });
    this.detail.createEl('p', { cls: 'reference-status', text: `${ACQUISITION[post.status] || post.status} · ${post.key}` });
    this.detail.createEl('p', { cls: 'reference-status', text: post.published === null ? 'Publication date unavailable' : `Published ${new Date(post.published).toLocaleString()}` });
    const memberships = this.detail.createEl('ul', { cls: 'reference-memberships' });
    const seen = new Set();
    for (const m of post.memberships) {
      const label = collectionLabel(this.lib, m.source, m.collection_id) + (m.active ? '' : ' (removed)');
      if (!seen.has(label)) memberships.createEl('li', { text: label });
      seen.add(label);
    }
    const stage = this.detail.createDiv();
    const members = this.detail.createDiv({ cls: 'reference-members' });
    const show = asset => {
      this.stopPreview(); stage.empty();
      for (const button of members.querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.asset === asset.id));
      const video = /\.(mp4|webm|mov)$/.test(asset.path);
      const preview = stage.createEl(video ? 'video' : 'img', { cls: 'reference-preview', attr: { 'aria-label': `Preview member ${asset.ordinal + 1}` } });
      this.preview = preview;
      const status = stage.createEl('p', { cls: 'reference-status', text: 'Connecting to the read-only archive…', attr: { 'aria-live': 'polite' } });
      const choose = stage.createEl('button', { text: video ? 'Choose full video or excerpt' : 'Add this image', cls: 'mod-cta' });
      choose.disabled = true;
      preview.addEventListener('error', () => { choose.disabled = true; status.textContent = 'Archive offline or file unavailable. Reconnect Media or VPN, then select this member again. Local thumbnails and existing cards are retained.'; });
      if (video) {
        preview.controls = true; preview.preload = 'metadata'; preview.autoplay = false;
        if (asset.thumbnail === `References/Thumbnails/${asset.id}.jpg`) preview.poster = this.app.vault.adapter.getResourcePath(asset.thumbnail);
        this.plugin.watchPlayer(preview);
        preview.addEventListener('loadedmetadata', () => { choose.disabled = false; status.textContent = `${preview.duration.toFixed(1)} seconds · click to play or seek`; });
      } else preview.addEventListener('load', () => { choose.disabled = false; status.textContent = 'Image from the read-only archive'; });
      try { preview.src = this.plugin.resourceURL(asset); }
      catch (error) { status.textContent = error.message; }
      choose.onclick = () => { this.close(); new CardEditor(this.plugin, this.board, { ...asset, title: post.title }).open(); };
    };
    for (const asset of post.assets) {
      const button = members.createEl('button', { cls: 'reference-member', attr: { 'aria-label': `Preview member ${asset.ordinal + 1}`, 'aria-pressed': 'false' } });
      button.dataset.asset = asset.id;
      this.thumbnail(button, asset, `Member ${asset.ordinal + 1}`);
      button.createEl('span', { text: `${asset.ordinal + 1} · ${/\.(mp4|webm|mov)$/.test(asset.path) ? 'Video' : 'Image'}` });
      button.onclick = () => show(asset);
    }
    const missing = post.expected.filter(m => !post.assets.some(a => a.ordinal === m.ordinal));
    if (missing.length) this.detail.createEl('p', { cls: 'reference-status', text: `Awaiting members: ${missing.map(m => `${m.ordinal + 1} (${m.kind})`).join(', ')}` });
    if (post.assets.length) show(post.assets[0]);
    else stage.createEl('p', { text: 'No archived media yet. The collector fetches independently of browsing; check References/Archive for acquisition status.' });
  }
}

class CardEditor extends Modal {
  constructor(plugin, board, asset, existing) {
    super(plugin.app); this.plugin = plugin; this.board = board; this.asset = validateAsset(asset); this.existing = existing;
  }
  async onOpen() {
    const { contentEl } = this;
    contentEl.createEl('h2', { text: this.existing ? 'Edit this reference' : 'Add a reference' });
    const card = this.existing?.card || { asset: this.asset, start: 0, end: 0, loop: false };
    const video = /\.(mp4|webm|mov)$/.test(this.asset.path);
    const preview = contentEl.createEl(video ? 'video' : 'img', { cls: 'reference-preview' });
    preview.src = this.plugin.resourceURL(this.asset);
    if (video) { preview.controls = true; preview.preload = 'metadata'; this.plugin.watchPlayer(preview); }
    const status = contentEl.createEl('p', { cls: 'reference-status', text: 'Loading from the read-only archive…' });
    preview.addEventListener('error', () => { status.textContent = 'Archive unavailable. Check the Media mount or VPN, then reopen this editor. Your reference is retained.'; });
    let title = this.existing?.file.basename || this.asset.title || 'Reference';
    new Setting(contentEl).setName('Card name').addText(t => t.setValue(title).onChange(v => title = v));
    let start = card.start, end = card.end, loop = card.loop;
    let mode = this.existing ? 'excerpt' : 'full';
    let startInput, endInput, modeInput;
    const excerpt = () => { mode = 'excerpt'; modeInput?.setValue(mode); };
    if (video) {
      new Setting(contentEl).setName('Add as').addDropdown(d => { modeInput = d; d.addOption('full', 'Full video').addOption('excerpt', 'Excerpt').setValue(mode).onChange(value => mode = value); });
      new Setting(contentEl).setName('Start (seconds)').addText(t => { startInput = t; t.inputEl.type = 'number'; t.inputEl.min = '0'; t.inputEl.step = '0.1'; t.setValue(String(start)).onChange(v => { start = Number(v); excerpt(); }); });
      new Setting(contentEl).setName('End (seconds)').addText(t => { endInput = t; t.inputEl.type = 'number'; t.inputEl.min = '0'; t.inputEl.step = '0.1'; t.setValue(String(end)).onChange(v => { end = Number(v); excerpt(); }); });
      new Setting(contentEl).setName('Use the player position')
        .addButton(b => b.setButtonText('Set start here').onClick(() => { excerpt(); start = Number(preview.currentTime.toFixed(3)); startInput.setValue(String(start)); }))
        .addButton(b => b.setButtonText('Set end here').onClick(() => { excerpt(); end = Number(preview.currentTime.toFixed(3)); endInput.setValue(String(end)); }));
      new Setting(contentEl).setName('Loop this excerpt').addToggle(t => t.setValue(loop).onChange(v => loop = v));
      preview.addEventListener('loadedmetadata', () => {
        if (!end) { end = preview.duration; endInput.setValue(String(end)); }
        preview.currentTime = start;
        status.textContent = `${preview.duration.toFixed(1)} seconds · one server original · this card owns its excerpt`;
      });
      new Setting(contentEl).addButton(b => b.setButtonText('Preview excerpt').onClick(() => {
        try { excerpt(); range(start, end, preview.duration); preview.currentTime = start; this.plugin.allowPlayback(preview); preview.play().catch(() => new Notice('Unable to play the archive file')); }
        catch (error) { new Notice(error.message); }
      }));
      preview.addEventListener('timeupdate', () => {
        if (mode === 'excerpt' && !preview.paused && end > start && preview.currentTime >= end) {
          if (loop) preview.currentTime = start;
          else { preview.pause(); preview.currentTime = end; }
        }
      });
      new Setting(contentEl).setName('Keep a still at the current position')
        .addButton(b => b.setButtonText('Capture frame on board').onClick(async () => {
          try { preview.pause(); await this.plugin.capture(this.board, this.asset, preview, title); new Notice('Frame added; the original is unchanged'); }
          catch (error) { new Notice(error.message); }
        }));
    } else preview.addEventListener('load', () => status.textContent = 'Image from the read-only archive');
    new Setting(contentEl).addButton(b => b.setButtonText(this.existing ? 'Save excerpt' : 'Add to board').setCta().onClick(async () => {
      try {
        if (video) { if (mode === 'full') { start = 0; end = preview.duration; loop = false; } range(start, end, preview.duration); }
        else if (!preview.naturalWidth) throw new Error('Wait for the archive image to load');
        const updated = { asset: this.asset, start, end, loop };
        if (this.existing) await this.app.vault.process(this.existing.file, text => replacePlayer(text, updated, this.plugin.fileURL(this.asset)));
        else await this.plugin.addCard(this.board, title, playerBlock(updated, this.plugin.fileURL(this.asset)) + '\n\nYour notes and annotations belong here.\n');
        this.close();
      } catch (error) { new Notice(error.message); }
    }));
    this.preview = preview;
  }
  onClose() { if (this.preview?.pause) this.preview.pause(); this.preview?.removeAttribute('src'); if (this.preview?.load) this.preview.load(); this.plugin.players.delete(this.preview); this.contentEl.empty(); }
}

module.exports = class ReferenceBoards extends Plugin {
  async onload() {
    this.settings = Object.assign({ archiveRoot: '', catalog: 'References/Catalog.json', projects: 'References/Projects' }, await this.loadData());
    this.players = new Set();
    this.allowedPlayers = new WeakSet();
    this.boardLeaves = new Map();
    const attach = doc => {
      // Media Extended renders in open shadow roots. Native play events do not
      // cross that boundary, so observe each root and listen on players directly.
      const roots = new Set();
      const visit = root => {
        if ([9, 11].includes(root.nodeType) && !roots.has(root)) {
          roots.add(root);
          const observer = new MutationObserver(records => {
            for (const record of records) for (const node of record.addedNodes) {
              if (node.nodeType === 1) visit(node);
            }
          });
          observer.observe(root, {childList: true, subtree: true});
          this.register(() => observer.disconnect());
        }
        const media = [...root.querySelectorAll('video,audio')];
        if (root.matches?.('video,audio')) media.push(root);
        for (const player of media) {
          this.watchPlayer(player);
        }
        if (root.shadowRoot) visit(root.shadowRoot);
        for (const element of root.querySelectorAll('*')) if (element.shadowRoot) visit(element.shadowRoot);
      };
      visit(doc);
      // Attaching a shadow root itself emits no mutation on its host.
      this.registerInterval(window.setInterval(() => visit(doc), 1000));
    };
    attach(document);
    this.registerEvent(this.app.workspace.on('window-open', (_, win) => attach(win.document)));
    this.addCommand({ id: 'add-reference', name: 'Add a reference to this board', callback: () => this.addReference().catch(e => new Notice(e.message)) });
    this.addCommand({ id: 'edit-reference', name: 'Choose excerpt or capture frame on this board', callback: () => this.editReference().catch(e => new Notice(e.message)) });
    this.addSettingTab(new class extends PluginSettingTab {
      constructor(app, plugin) { super(app, plugin); this.plugin = plugin; }
      display() {
        this.containerEl.empty();
        new Setting(this.containerEl).setName('Read-only archive folder').setDesc('Configured by the desktop installer. Videos remain outside the vault.')
          .addText(t => t.setValue(this.plugin.settings.archiveRoot).onChange(async v => { this.plugin.settings.archiveRoot = v; await this.plugin.saveData(this.plugin.settings); }));
      }
    }(this.app, this));
  }
  watchPlayer(player) {
    if (this.players.has(player)) return;
    this.players.add(player);
    player.autoplay = false;
    player.pause();
    const controls = player.getRootNode();
    const target = controls.nodeType === 11 ? controls : player;
    this.registerDomEvent(target, 'pointerdown', () => this.allowPlayback(player));
    this.registerDomEvent(target, 'keydown', event => {
      if ([' ', 'Enter'].includes(event.key)) this.allowPlayback(player);
    });
    this.registerDomEvent(player, 'play', () => {
      if (!this.allowedPlayers.has(player)) { player.pause(); return; }
      for (const other of this.players) {
        if (!other.isConnected) { other.pause(); this.players.delete(other); }
        else if (other !== player) other.pause();
      }
    });
  }
  allowPlayback(player) { this.allowedPlayers.add(player); }
  onunload() { for (const player of this.players) if (player.isConnected) player.pause(); this.players.clear(); }
  fileURL(asset) {
    validateAsset(asset);
    if (!path.isAbsolute(this.settings.archiveRoot)) throw new Error('The archive folder has not been installed');
    return pathToFileURL(path.join(this.settings.archiveRoot, asset.path)).href;
  }
  resourceURL(asset) { return Platform.resourcePathPrefix + this.fileURL(asset).slice(8); }
  board() {
    // Selected embedded notes can become getActiveFile(); target their Canvas.
    let leaf = this.app.workspace.getMostRecentLeaf();
    const types = ['canvas', 'excalidraw'];
    if (!types.includes(leaf?.view.getViewType())) {
      const visible = types.flatMap(type => this.app.workspace.getLeavesOfType(type)).filter(l => l.view.containerEl.isShown());
      leaf = visible.length === 1 ? visible[0] : null;
    }
    const file = types.includes(leaf?.view.getViewType()) ? leaf.view.file : null;
    if (!file) throw new Error('Open an Excalidraw or Canvas board first');
    this.boardLeaves.set(file.path, leaf);
    if (file.path.startsWith('Blog/')) throw new Error('Use a private board outside Blog');
    if (!this.app.plugins.enabledPlugins.has('media-extended')) throw new Error('Enable Media Extended for inline board playback');
    return file;
  }
  async addReference() {
    const board = this.board();
    const catalog = JSON.parse(await this.app.vault.adapter.read(this.settings.catalog));
    new CollectionBrowser(this, board, catalog).open();
  }
  async editReference() {
    const board = this.board(), items = [];
    let paths;
    if (board.extension === 'canvas') paths = JSON.parse(await this.app.vault.read(board)).nodes.map(n => n.file);
    else {
      const ea = window.ExcalidrawAutomate.getAPI(this.boardLeaves.get(board.path).view);
      try { paths = ea.getViewElements().filter(n => !n.isDeleted).map(n => n.customData?.referenceNote); }
      finally { ea.destroy(); }
    }
    for (const notePath of new Set(paths.filter(Boolean))) {
      const file = this.app.vault.getFileByPath(notePath);
      if (file?.extension !== 'md') continue;
      const card = readCard(await this.app.vault.read(file));
      if (card) items.push({ file, card, label: file.basename });
    }
    if (!items.length) throw new Error('Add a reference with Reference Boards first');
    new Picker(this.app, items, item => new CardEditor(this, board, item.card.asset, item).open(), 'Choose the card to edit or capture').open();
  }
  async folder(name) { if (!this.app.vault.getAbstractFileByPath(name)) await this.app.vault.createFolder(name); }
  async addCard(board, title, body) {
    const slug = title.replace(/[\\/:*?"<>|\[\]#\r\n]/g, ' ').trim().slice(0, 90) || 'Reference';
    const folder = this.settings.projects;
    const project = board.basename.replace(/[\\/:*?"<>|\[\]#\r\n]/g, ' ').slice(0, 70);
    await this.folder(folder);
    const file = await this.app.vault.create(`${folder}/${project} — ${slug}-${crypto.randomUUID().slice(0, 8)}.md`, `---\nprivate: true\n---\n\n# ${slug}\n\n${body}`);
    const leaf = this.boardLeaves.get(board.path);
    if (!leaf) throw new Error('Reopen this board; the reference note was retained');
    if (leaf.view.file?.path !== board.path) await leaf.openFile(board);
    if (board.extension !== 'canvas') {
      const ea = window.ExcalidrawAutomate.getAPI(leaf.view);
      try {
        const elements = ea.getViewElements().filter(n => !n.isDeleted);
        const right = Math.max(0, ...elements.map(n => n.x + n.width + 40));
        const id = ea.addEmbeddable(right, 0, 480, 440, undefined, file);
        ea.elementsDict[id].customData = {...ea.elementsDict[id].customData, referenceNote: file.path};
        if (!await ea.addElementsToView(false, true, true)) throw new Error('Could not add the card; its note was retained');
      } finally { ea.destroy(); }
      return file;
    }
    await this.app.vault.process(board, text => {
      const data = JSON.parse(text); data.nodes ||= [];
      const right = Math.max(0, ...data.nodes.map(n => n.x + n.width + 40));
      data.nodes.push({ id: crypto.randomUUID().replaceAll('-', ''), type: 'file', file: file.path, x: right, y: 0, width: 480, height: 440 });
      return JSON.stringify(data, null, 2);
    });
    return file;
  }
  async capture(board, asset, video, title) {
    if (video.readyState < 2 || !video.videoWidth) throw new Error('Load a video frame first');
    const canvas = document.createElement('canvas');
    canvas.width = Math.min(1280, video.videoWidth); canvas.height = Math.round(canvas.width * video.videoHeight / video.videoWidth);
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.88));
    if (!blob) throw new Error('The player could not capture this frame');
    const folder = 'References/Frames'; await this.folder(folder);
    const seconds = Number(video.currentTime.toFixed(3));
    const file = `${folder}/${asset.id}-${seconds}-${crypto.randomUUID().slice(0, 8)}.jpg`;
    await this.app.vault.createBinary(file, await blob.arrayBuffer());
    await this.addCard(board, `${title} at ${seconds}s`, `![[${file}]]\n\n[Original at ${seconds}s](${this.fileURL(asset)}#t=${seconds})\n\nAsset: \`${asset.id}\`\n\nYour annotation:\n`);
  }
};
