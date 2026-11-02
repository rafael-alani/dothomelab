const { Plugin, Modal, FuzzySuggestModal, Notice, Platform, PluginSettingTab, Setting } = require('obsidian');
const path = require('path');
const { pathToFileURL } = require('url');
const { validateAsset, range, readCard, playerBlock, replacePlayer } = require('./model.cjs');

class Picker extends FuzzySuggestModal {
  constructor(app, items, choose, prompt) { super(app); this.items = items; this.choose = choose; this.setPlaceholder(prompt); }
  getItems() { return this.items; }
  getItemText(item) { return item.label || item.title || item.path; }
  onChooseItem(item) { this.choose(item); }
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
    if (video) { preview.controls = true; preview.preload = 'metadata'; }
    const status = contentEl.createEl('p', { cls: 'reference-status', text: 'Loading from the read-only archive…' });
    preview.addEventListener('error', () => { status.textContent = 'Archive unavailable. Check the Media mount or VPN, then reopen this editor. Your reference is retained.'; });
    let title = this.existing?.file.basename || this.asset.title || 'Reference';
    new Setting(contentEl).setName('Card name').addText(t => t.setValue(title).onChange(v => title = v));
    let start = card.start, end = card.end, loop = card.loop;
    let startInput, endInput;
    if (video) {
      new Setting(contentEl).setName('Start (seconds)').addText(t => { startInput = t; t.inputEl.type = 'number'; t.inputEl.min = '0'; t.inputEl.step = '0.1'; t.setValue(String(start)).onChange(v => start = Number(v)); });
      new Setting(contentEl).setName('End (seconds)').addText(t => { endInput = t; t.inputEl.type = 'number'; t.inputEl.min = '0'; t.inputEl.step = '0.1'; t.setValue(String(end)).onChange(v => end = Number(v)); });
      new Setting(contentEl).setName('Use the player position')
        .addButton(b => b.setButtonText('Set start here').onClick(() => { start = Number(preview.currentTime.toFixed(3)); startInput.setValue(String(start)); }))
        .addButton(b => b.setButtonText('Set end here').onClick(() => { end = Number(preview.currentTime.toFixed(3)); endInput.setValue(String(end)); }));
      new Setting(contentEl).setName('Loop this excerpt').addToggle(t => t.setValue(loop).onChange(v => loop = v));
      preview.addEventListener('loadedmetadata', () => {
        if (!end) { end = preview.duration; endInput.setValue(String(end)); }
        preview.currentTime = start;
        status.textContent = `${preview.duration.toFixed(1)} seconds · one server original · this card owns its excerpt`;
      });
      new Setting(contentEl).addButton(b => b.setButtonText('Preview excerpt').onClick(() => {
        try { range(start, end, preview.duration); preview.currentTime = start; preview.play().catch(() => new Notice('Unable to play the archive file')); }
        catch (error) { new Notice(error.message); }
      }));
      preview.addEventListener('timeupdate', () => {
        if (!preview.paused && end > start && preview.currentTime >= end) {
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
        if (video) range(start, end, preview.duration);
        else if (!preview.naturalWidth) throw new Error('Wait for the archive image to load');
        const updated = { asset: this.asset, start, end, loop };
        if (this.existing) await this.app.vault.process(this.existing.file, text => replacePlayer(text, updated, this.plugin.fileURL(this.asset)));
        else await this.plugin.addCard(this.board, title, playerBlock(updated, this.plugin.fileURL(this.asset)) + '\n\nYour notes and annotations belong here.\n');
        this.close();
      } catch (error) { new Notice(error.message); }
    }));
    this.preview = preview;
  }
  onClose() { if (this.preview?.pause) this.preview.pause(); this.preview?.removeAttribute('src'); this.contentEl.empty(); }
}

module.exports = class ReferenceBoards extends Plugin {
  async onload() {
    this.settings = Object.assign({ archiveRoot: '', catalog: 'References/Catalog.json', projects: 'References/Projects' }, await this.loadData());
    this.players = new Set();
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
          if (this.players.has(player)) continue;
          this.players.add(player);
          this.registerDomEvent(player, 'play', () => {
            for (const other of this.players) {
              if (!other.isConnected) this.players.delete(other);
              else if (other !== player) other.pause();
            }
          });
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
    const items = catalog.assets.map(asset => ({ ...validateAsset(asset), label: `${asset.title || 'Reference'} · ${(asset.collections || []).join(' / ')} · ${asset.id.slice(0, 8)}` }));
    new Picker(this.app, items, asset => new CardEditor(this, board, asset).open(), 'Find a reference by title or collection').open();
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
    const file = await this.app.vault.create(`${folder}/${project} — ${slug}-${crypto.randomUUID().slice(0, 8)}.md`, `# ${slug}\n\n${body}`);
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
