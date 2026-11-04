const { Plugin, Modal, FuzzySuggestModal, Notice, Platform, PluginSettingTab, Setting } = require('obsidian');
const path = require('path');
const { pathToFileURL } = require('url');
const fs = require('fs/promises');
const { execFile } = require('child_process');
const { MODEL, DEFAULTS, supported, buildBrief, stamp } = require('./context.cjs');
const { validateAsset, range, readCard, playerBlock, replacePlayer, library, browse, collectionLabel, collectionTrail, childCollections } = require('./model.cjs');

class Picker extends FuzzySuggestModal {
  constructor(app, items, choose, prompt) { super(app); this.items = items; this.choose = choose; this.setPlaceholder(prompt); }
  getItems() { return this.items; }
  getItemText(item) { return item.label || item.title || item.path; }
  onChooseItem(item) { this.choose(item); }
}

const ACQUISITION = { archived: 'Archived', pending: 'Awaiting acquisition', retry: 'Unavailable · retry scheduled', partial: 'Partially archived', unverified: 'Media available · completion unverified' };

class CollectionBrowser extends Modal {
  constructor(plugin, board, catalog, mode = 'board') {
    super(plugin.app);
    this.plugin = plugin; this.board = board; this.lib = library(catalog);
    this.search = ''; this.order = 'source'; this.history = false; this.mode = mode;
    this.selected = new Map(); this.receipts = new Map(); this.reads = new Map(); this.task = '';
    this.previewVersion = 0; this.closed = false;
  }
  onOpen() {
    this.modalEl.addClass('reference-browser');
    this.page = this.contentEl.createDiv({ cls: 'reference-browser-page' });
    if (this.mode === 'context') { this.modalEl.addClass('reference-context'); this.contextControls(); }
    this.showSources();
  }
  stopPreview() {
    this.previewVersion++; this.previewAsset = null;
    if (this.preview?.pause) this.preview.pause();
    if (this.preview) {
      this.preview.removeAttribute('src');
      if (this.preview.load) this.preview.load();
      this.plugin.players.delete(this.preview);
    }
    this.preview = null;
  }
  onClose() { this.closed = true; this.stopPreview(); this.contentEl.empty(); }
  heading(title, back, action) {
    this.stopPreview(); this.page.empty(); this.grid = null; this.detail = null;
    if (back) this.page.createEl('button', { text: back }).onclick = action;
    this.page.createEl('h2', { text: title });
  }
  showSources() {
    this.source = null; this.collection = null;
    this.heading(this.mode === 'context' ? 'Create an agent brief' : 'Add a reference');
    this.page.createEl('p', { text: this.mode === 'context'
      ? 'Choose a source and folder. Preview cards independently; check videos in the order you want them cited.'
      : 'Choose a source, then a folder. Preview before adding to your board.' });
    const sources = [...new Set([...this.lib.collections.values()].map(c => c.source))];
    for (const source of sources) {
      const button = this.page.createEl('button', { cls: 'reference-collection', text: source[0].toUpperCase() + source.slice(1) });
      button.onclick = () => { this.source = source; this.showCollections(); };
    }
    if (!sources.length) this.page.createEl('p', { text: 'Collection metadata is not available. Run the desktop collector to refresh this older catalog. Existing board cards still work.' });
  }
  breadcrumbs() {
    const nav = this.page.createEl('nav', { cls: 'reference-breadcrumbs', attr: { 'aria-label': 'Collection path' } });
    nav.createEl('button', { text: 'Sources' }).onclick = () => this.showSources();
    const trail = collectionTrail(this.lib, this.source, this.collection?.id);
    const crumbs = [{ title: this.source[0].toUpperCase() + this.source.slice(1), id: null }, ...trail];
    for (const [index, c] of crumbs.entries()) {
      nav.createEl('span', { text: '/', attr: { 'aria-hidden': 'true' } });
      if (index === crumbs.length - 1) nav.createEl('span', { text: c.title, attr: { 'aria-current': 'location' } });
      else nav.createEl('button', { text: c.title }).onclick = () => c.id === null ? this.showCollections() : this.openCollection(c);
    }
  }
  openCollection(collection) {
    this.collection = collection; this.search = ''; this.history = !collection.active; this.showCollection();
  }
  goBack() {
    const trail = collectionTrail(this.lib, this.source, this.collection?.id);
    if (trail.length > 1) this.openCollection(trail[trail.length - 2]);
    else if (this.collection) this.showCollections();
    else this.showSources();
  }
  showCollections() {
    this.collection = null;
    this.heading('Choose a folder', 'Back', () => this.goBack());
    this.breadcrumbs(); this.folderList();
  }
  folderList() {
    const parent = this.collection?.id ?? null;
    if (parent !== null && !childCollections(this.lib, this.source, parent).length) return;
    const section = this.page.createDiv({ cls: 'reference-folder-section' });
    const scope = parent === null ? `${this.source} top-level folders` : 'immediate subfolders';
    const filter = section.createEl('input', { type: 'search', placeholder: `Find ${scope}`, attr: { 'aria-label': `Find ${scope}` } });
    const list = section.createDiv({ cls: 'reference-collections' });
    const render = () => {
      list.empty();
      for (const c of childCollections(this.lib, this.source, parent, filter.value)) {
        const current = browse(this.lib, c.source, c.id).length;
        const removed = browse(this.lib, c.source, c.id, { history: true }).length;
        const children = childCollections(this.lib, c.source, c.id).length;
        const button = list.createEl('button', { cls: 'reference-collection', text: `${c.title || '(unnamed collection)'} · ${current} posts${removed ? ` · ${removed} removed` : ''}${children ? ` · ${children} subfolders` : ''}${c.active ? '' : ' · removed collection'}` });
        button.onclick = () => this.openCollection(c);
      }
      if (!list.children.length) list.createEl('p', { text: 'No matching folders at this level.' });
    };
    filter.oninput = render; render();
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
    this.heading(this.collection.title || '(unnamed collection)', 'Back', () => this.goBack());
    this.breadcrumbs(); this.folderList();
    const source = Array.isArray(this.lib.sources) && this.lib.sources.find(s => s.source === this.source);
    const stamp = source?.received ? new Date(source.received * 1000).toLocaleString() : 'unknown';
    this.page.createEl('p', { cls: 'reference-status', text: `Inventory: ${source?.status || 'unknown'} · ${stamp}. Scan completion does not certify source-count parity.` });
    if (this.collection.audit) {
      const audit = this.collection.audit;
      this.page.createEl('p', { cls: 'reference-status', text: `Source grid: ${audit.ui_posts} posts · checked ${new Date(audit.checked_at * 1000).toLocaleString()}${audit.api_only?.length ? ' · API/grid mismatch; historical membership retained' : ''}` });
    }
    const controls = this.page.createDiv({ cls: 'reference-browser-controls' });
    const search = controls.createEl('input', { type: 'search', placeholder: 'Search within this collection', attr: { 'aria-label': 'Search within this collection' } });
    search.value = this.search;
    const order = controls.createEl('select', { attr: { 'aria-label': 'Post order' } });
    for (const [value, text] of [['source', 'Source collection order'], ['newest', 'Published: newest first'], ['oldest', 'Published: oldest first']]) order.createEl('option', { value, text });
    order.value = this.order;
    const history = controls.createEl('select', { attr: { 'aria-label': 'Membership status' } });
    for (const [value, text] of [['current', 'Current contents'], ['removed', 'Removed memberships']]) history.createEl('option', { value, text });
    history.value = this.history ? 'removed' : 'current';
    this.summary = this.page.createEl('p', { cls: 'reference-status', attr: { 'aria-live': 'polite' } });
    const body = this.page.createDiv({ cls: 'reference-browser-body' });
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
      const card = this.grid.createDiv({ cls: 'reference-post-card' });
      const button = card.createEl('button', { cls: 'reference-post', attr: { 'aria-label': `Preview ${post.title}`, 'aria-pressed': 'false' } });
      this.thumbnail(button, post.assets.find(a => a.thumbnail) || (post.thumbnail ? { thumbnail: post.thumbnail } : null), post.title);
      button.createEl('span', { cls: 'reference-post-title', text: post.title });
      const videoCount = post.assets.filter(a => /\.(mp4|webm|mov)$/.test(a.path)).length;
      button.createEl('span', { cls: 'reference-post-meta', text: `${post.assets.length} media${videoCount ? ` · ${videoCount} video` : ''} · ${ACQUISITION[post.status] || post.status}` });
      button.onclick = () => {
        for (const other of this.grid.querySelectorAll('button')) other.setAttribute('aria-pressed', String(other === button));
        this.showPost(post);
      };
      if (this.mode === 'context') {
        const choices = card.createDiv({ cls: 'reference-video-choices' });
        for (const asset of post.assets.filter(a => /\.(mp4|webm|mov)$/.test(a.path))) this.selectionControl(choices, post, asset);
        if (!videoCount) choices.createEl('span', { cls: 'reference-status', text: 'No archived videos to select' });
      }
    }
    this.detail.createEl('p', { text: posts.length ? 'Select a post to preview its media. Videos start paused.' : 'No posts match this collection and search. Removed memberships are available separately.' });
  }
  showPost(post) {
    this.stopPreview(); this.detail.empty();
    this.detail.createEl('h3', { text: post.title });
    this.detail.createEl('p', { cls: 'reference-status', text: `${ACQUISITION[post.status] || post.status} · ${post.key}` });
    if (post.savedCopy) this.detail.createEl('p', { cls: 'reference-status', text: 'Archived from the retained Yaay media. The original platform link may be unavailable.' });
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
      const choose = this.mode === 'board' ? stage.createEl('button', { text: video ? 'Choose full video or excerpt' : 'Add this image', cls: 'mod-cta' }) : {};
      choose.disabled = true;
      preview.addEventListener('error', () => { choose.disabled = true; status.textContent = 'Archive offline or file unavailable. Reconnect Media or VPN, then select this member again. Local thumbnails and existing cards are retained.'; });
      if (video) {
        preview.controls = true; preview.preload = 'metadata'; preview.autoplay = false;
        if (asset.thumbnail === `References/Thumbnails/${asset.id}.jpg`) preview.poster = this.app.vault.adapter.getResourcePath(asset.thumbnail);
        this.plugin.watchPlayer(preview);
        // Native media accessibility actions need not emit pointerdown/keydown.
        const play = stage.createEl('button', { text: 'Play preview' });
        play.onclick = () => {
          if (!preview.paused) preview.pause();
          else { this.plugin.allowPlayback(preview); preview.play().catch(() => { status.textContent = 'Unable to play. Reconnect Media or VPN and select this member again.'; }); }
        };
        preview.addEventListener('play', () => play.textContent = preview.paused ? 'Play preview' : 'Pause preview');
        preview.addEventListener('pause', () => play.textContent = 'Play preview');
        preview.addEventListener('loadedmetadata', () => { choose.disabled = false; status.textContent = `${preview.duration.toFixed(1)} seconds · click to play or seek`; });
      } else preview.addEventListener('load', () => { choose.disabled = false; status.textContent = 'Image from the read-only archive'; });
      try { preview.src = this.plugin.resourceURL(asset); }
      catch (error) { status.textContent = error.message; }
      choose.onclick = () => { this.close(); new CardEditor(this.plugin, this.board, { ...asset, title: post.title }).open(); };
      if (video) {
        this.previewAsset = asset;
        this.transcriptPanel = stage.createDiv({ cls: 'reference-transcript' });
        this.showTranscript(asset, preview, this.transcriptPanel);
      }
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
  selectionControl(parent, post, asset) {
    const label = parent.createEl('label', { cls: 'reference-video-choice' });
    const checkbox = label.createEl('input', { type: 'checkbox', attr: { 'aria-label': `Select ${post.title} · video member ${asset.ordinal + 1}` } });
    checkbox.dataset.asset = asset.id; checkbox.checked = this.selected.has(asset.id);
    label.setAttribute('data-selected', String(checkbox.checked));
    label.createEl('span', { text: `Video member ${asset.ordinal + 1}` });
    checkbox.onchange = () => {
      if (this.saving || (checkbox.checked && !this.selected.has(asset.id) && this.selected.size >= 50)) {
        checkbox.checked = this.selected.has(asset.id); new Notice(this.saving ? 'Saving the selected videos…' : 'Select at most 50 videos per brief.'); return;
      }
      if (checkbox.checked) this.selected.set(asset.id, { ...asset, title: post.title });
      else this.selected.delete(asset.id);
      this.selectionStatus();
      if (checkbox.checked) this.cachedTranscript(asset.id).catch(() => {});
    };
  }
  contextControls() {
    const footer = this.contentEl.createDiv({ cls: 'reference-context-footer' });
    this.selectionSummary = footer.createEl('p', { cls: 'reference-status', attr: { 'aria-live': 'polite' } });
    const selected = footer.createEl('details', { cls: 'reference-selected' });
    this.selectedHeading = selected.createEl('summary', { text: 'Review selected videos' });
    this.selectedList = selected.createDiv();
    this.clear = footer.createEl('button', { text: 'Clear selection' });
    this.clear.onclick = () => { if (!this.saving) { this.selected.clear(); this.selectionStatus(); } };
    footer.createEl('label', { text: 'What should the agent do?', attr: { for: 'reference-context-task' } });
    const task = footer.createEl('textarea', { cls: 'reference-context-task', attr: { id: 'reference-context-task', rows: '2', placeholder: 'Describe the task and what to learn from these videos.' } });
    task.oninput = () => this.task = task.value;
    const actions = footer.createDiv({ cls: 'reference-context-actions' });
    this.request = actions.createEl('button', { text: 'Request / refresh transcripts' });
    this.request.onclick = async () => {
      this.request.disabled = true;
      try {
        const ids = [...this.selected.keys()];
        if (!ids.length) throw new Error('Select at least one archived video.');
        // Finish older cache reads before refreshing the same evidence.
        await Promise.allSettled(ids.map(id => this.reads.get(id)));
        const receipts = await this.plugin.archiveRequest({ action: 'request_transcripts', asset_ids: ids, model: MODEL });
        for (const receipt of receipts) this.receipts.set(receipt.asset_id, receipt);
        if (this.closed) return;
        this.selectionStatus();
        if (this.previewAsset && ids.includes(this.previewAsset.id)) this.showTranscript(this.previewAsset, this.preview, this.transcriptPanel);
      } catch (e) { if (!this.closed) this.selectionSummary.textContent = e.message; }
      finally { this.request.disabled = this.saving; }
    };
    this.save = actions.createEl('button', { text: 'Save agent brief', cls: 'mod-cta' });
    this.save.onclick = async () => {
      this.saving = true; this.save.disabled = true; this.request.disabled = true;
      const selection = [...this.selected.values()], instruction = this.task;
      try {
        await Promise.all(selection.map(a => this.cachedTranscript(a.id)));
        if (this.closed) return;
        const file = await this.plugin.saveBrief(instruction, selection, [...this.receipts.values()]);
        this.close(); await this.app.workspace.getLeaf(false).openFile(file);
        new Notice('Private brief saved. Give this note and its evidence to your agent.');
      } catch (e) { if (!this.closed) this.selectionSummary.textContent = e.message; }
      finally { this.saving = false; this.save.disabled = false; this.request.disabled = false; }
    };
    this.selectionStatus();
  }
  selectionStatus() {
    if (this.mode !== 'context' || this.closed) return;
    const counts = {};
    for (const id of this.selected.keys()) {
      const status = this.reads.has(id) ? 'loading' : this.receipts.get(id)?.status || 'not checked';
      counts[status] = (counts[status] || 0) + 1;
    }
    this.selectionSummary.textContent = `${this.selected.size}/50 selected · ${Object.entries(counts).map(([k, v]) => `${v} ${k}`).join(' · ') || 'Check video members to select them'}. Export requires every selected transcript.`;
    this.selectedHeading.textContent = `Review selected videos (${this.selected.size})`;
    this.clear.disabled = !this.selected.size;
    this.selectedList.empty();
    for (const [index, asset] of [...this.selected.values()].entries()) {
      const row = this.selectedList.createDiv({ cls: 'reference-selected-row' });
      row.createEl('span', { text: `${index + 1}. ${asset.title} · video member ${asset.ordinal + 1}` });
      row.createEl('button', { text: 'Remove', attr: { 'aria-label': `Remove ${asset.title} · video member ${asset.ordinal + 1}` } }).onclick = () => {
        if (!this.saving) { this.selected.delete(asset.id); this.selectionStatus(); }
      };
    }
    for (const input of this.grid?.querySelectorAll('input') || []) {
      input.checked = this.selected.has(input.dataset.asset);
      input.parentElement.setAttribute('data-selected', String(input.checked));
    }
  }
  cachedTranscript(id, refresh = false) {
    if (!refresh && this.receipts.get(id)?.status === 'ready') return Promise.resolve(this.receipts.get(id));
    if (this.reads.has(id)) return this.reads.get(id);
    const read = this.plugin.archiveRequest({ action: 'transcripts', asset_ids: [id], model: MODEL }).then(rows => {
      const receipt = rows.find(r => r.asset_id === id && r.model === MODEL);
      if (!receipt) throw new Error('Transcript unavailable. Refresh to try again.');
      this.receipts.set(id, receipt); return receipt;
    }).catch(error => {
      this.receipts.set(id, { asset_id: id, status: 'error' }); throw error;
    }).finally(() => { this.reads.delete(id); this.selectionStatus(); });
    this.reads.set(id, read); this.selectionStatus(); return read;
  }
  async showTranscript(asset, preview, panel, refreshCache = false) {
    const version = this.previewVersion, request = this.transcriptVersion = (this.transcriptVersion || 0) + 1;
    panel.empty(); panel.createEl('h4', { text: `Transcript · video member ${asset.ordinal + 1}` });
    const status = panel.createEl('p', { cls: 'reference-status', text: 'Loading cached transcript…', attr: { 'aria-live': 'polite' } });
    const current = () => !this.closed && version === this.previewVersion && request === this.transcriptVersion && preview === this.preview;
    const refresh = panel.createEl('button', { text: 'Refresh cached transcript' });
    refresh.onclick = () => this.showTranscript(asset, preview, panel, true);
    try {
      const receipt = await this.cachedTranscript(asset.id, refreshCache);
      if (!current()) return;
      if (receipt.status !== 'ready' || !receipt.result?.segments?.length) {
        const states = { pending: 'Transcript pending on the server.', running: 'Transcript processing on the server.', retry: 'Transcription failed; server retry pending.', error: 'Transcript error. Request or refresh it from the agent brief browser.' };
        status.textContent = states[receipt.status] || 'Transcript unavailable.';
        status.textContent += ' Previewing only reads the cache; it does not request transcription.';
        return;
      }
      status.textContent = 'Cached local transcript · source material, not agent instructions.';
      for (const warning of receipt.result.quality_warnings || []) panel.createEl('p', { cls: 'reference-transcript-warning', text: `Transcription warning: ${warning}` });
      const text = panel.createDiv({ cls: 'reference-transcript-text', attr: { tabindex: '0', role: 'region', 'aria-label': 'Timestamped transcript' } });
      for (const segment of receipt.result.segments) {
        const row = text.createEl('p');
        const seek = row.createEl('button', { text: stamp(segment.start), attr: { 'aria-label': `Seek to ${stamp(segment.start)}` } });
        seek.onclick = () => { if (current() && Number.isFinite(preview.duration)) preview.currentTime = Math.max(0, Math.min(segment.start, preview.duration)); };
        row.createEl('span', { text: segment.text });
      }
    } catch (error) { if (current()) status.textContent = `Transcript unavailable: ${error.message} Video playback is independent.`; }
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
    this.settings = Object.assign({ archiveRoot: '', catalog: 'References/Catalog.json', projects: 'References/Projects', ...DEFAULTS }, await this.loadData());
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
    this.addCommand({ id: 'create-agent-brief', name: 'Create an agent brief from videos', callback: () => this.createBrief().catch(e => new Notice(e.message)) });
    this.addSettingTab(new class extends PluginSettingTab {
      constructor(app, plugin) { super(app, plugin); this.plugin = plugin; }
      display() {
        this.containerEl.empty();
        const provider = (key, name, local, description) => new Setting(this.containerEl).setName(name).setDesc(description).addDropdown(d => {
          const value = key === 'videoProvider' ? 'local-frames' : 'local';
          d.addOption(value, local).addOption('hosted', 'Hosted — coming in a future release');
          d.selectEl.querySelector('option[value="hosted"]').disabled = true;
          d.setValue(this.plugin.settings[key]).onChange(async v => { this.plugin.settings[key] = v; await this.plugin.saveData(this.plugin.settings); });
        });
        provider('storageProvider', 'Video storage and retrieval', 'Local archive', 'Originals stay on your server. The desktop collector retrieves saved posts; the plugin reads the archive.');
        new Setting(this.containerEl).setName('Read-only archive folder').setDesc('Configured by the desktop installer. Videos remain outside the vault.')
          .addText(t => t.setValue(this.plugin.settings.archiveRoot).onChange(async v => { this.plugin.settings.archiveRoot = v; await this.plugin.saveData(this.plugin.settings); }));
        provider('speechProvider', 'Speech-to-text', 'Local server', 'Whisper runs on the homelab, never on this Mac. Cached transcripts become available after acquisition.');
        new Setting(this.containerEl).setName('Local speech model').setDesc('Whisper large-v3-turbo · CPU int8. The shared service manages the model and credentials.').addDropdown(d => d.addOption(MODEL, 'Whisper large-v3-turbo').setValue(this.plugin.settings.speechModel));
        provider('videoProvider', 'Video understanding', 'Local captured frames', 'Use the existing capture-frame command and attach selected frames to your agent. Automatic visual analysis is not enabled in this release. This choice is independent of storage and speech.');
        new Setting(this.containerEl).setName('Archive connection').setDesc('Uses the desktop collector’s private connection. No API key is saved in your vault.').addButton(b => b.setButtonText('Test connection').onClick(async () => {
          b.setDisabled(true);
          try { await this.plugin.archiveRequest({ action: 'status' }); new Notice('Local archive connection works.'); }
          catch (e) { new Notice(e.message); }
          finally { b.setDisabled(false); }
        }));
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
    if (this.settings.storageProvider && this.settings.storageProvider !== 'local') throw new Error('Hosted storage is not available in this release.');
    validateAsset(asset);
    if (!path.isAbsolute(this.settings.archiveRoot)) throw new Error('The archive folder has not been installed');
    return pathToFileURL(path.join(this.settings.archiveRoot, asset.path)).href;
  }
  resourceURL(asset) {
    // Request the resource afresh after a reconnect, as the existing file
    // player does. Stored immutable file URLs remain unchanged.
    return Platform.resourcePathPrefix + this.fileURL(asset).slice(8) + '?' + Date.now();
  }
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
  async archiveRequest(header) {
    supported(this.settings);
    if (!this.settings.connectionFile || !path.isAbsolute(this.settings.connectionFile)) throw new Error('Install the desktop collector connection before requesting transcripts.');
    const config = JSON.parse(await fs.readFile(this.settings.connectionFile, 'utf8'));
    if (!/^[a-zA-Z0-9][a-zA-Z0-9.-]*$/.test(config.host)) throw new Error('Invalid archive server name.');
    const key = path.join(path.dirname(this.settings.connectionFile), 'ingest-key');
    return new Promise((resolve, reject) => {
      const process = execFile('ssh', ['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=8','-o','IdentitiesOnly=yes','-i',key,`reference-ingest@${config.host}`], { timeout: 30000, maxBuffer: 32 * 1024 * 1024 }, (error, stdout) => {
        if (error) return reject(new Error('Archive unavailable. Check your server or VPN connection, then refresh.'));
        try { const response = JSON.parse(stdout); if (!response.ok) throw new Error(); resolve(response.result); }
        catch (_) { reject(new Error('The archive rejected this request. Update the collector and server together.')); }
      });
      process.stdin.on('error', () => {});
      process.stdin.end(JSON.stringify(header) + '\n');
    });
  }
  async createBrief() {
    supported(this.settings);
    const catalog = JSON.parse(await this.app.vault.adapter.read(this.settings.catalog));
    new CollectionBrowser(this, null, catalog, 'context').open();
  }
  async saveBrief(task, selection, receipts) {
    supported(this.settings);
    const { markdown, manifest } = buildBrief(task, selection, receipts);
    const folder = this.settings.briefs;
    if (folder !== 'References/Briefs') throw new Error('Briefs must be saved in the private References/Briefs folder.');
    await this.folder(folder);
    const stem = `${folder}/Agent brief ${new Date().toISOString().replace(/[:.]/g, '-')}-${crypto.randomUUID().slice(0,8)}`;
    await this.app.vault.create(stem + '.json', JSON.stringify(manifest, null, 2));
    return this.app.vault.create(stem + '.md', markdown);
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
