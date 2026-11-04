const START = '<!-- reference-player:start -->';
const END = '<!-- reference-player:end -->';
const MARKER = /<!-- reference-card:(.*?) -->/;

function validateAsset(asset) {
  if (!asset || !/^[a-f0-9]{64}$/.test(asset.id) ||
      !new RegExp('^objects/' + asset.id + '\\.(mp4|webm|mov|jpg|jpeg|png|webp)$').test(asset.path)) {
    throw new Error('Invalid immutable archive reference');
  }
  return asset;
}

function range(start, end, duration) {
  if (!Number.isFinite(start) || !Number.isFinite(end) || !Number.isFinite(duration) ||
      start < 0 || end <= start || end > duration + 0.05) throw new Error('Choose a start before the end, within the video');
  return { start, end };
}

function readCard(text) {
  const match = text.match(MARKER);
  return match ? JSON.parse(match[1]) : null;
}

function playerBlock(card, url) {
  validateAsset(card.asset);
  const metadata = JSON.stringify(card).replaceAll('<', '\\u003c');
  const media = /\.(mp4|webm|mov)$/.test(card.asset.path)
    ? `![Reference|440](${url}#t=${card.start},${card.end}&no_autoplay&${card.loop ? 'loop' : 'no_loop'}&load=eager)`
    : `![Reference|440](${url})`;
  const thumbnail = card.asset.thumbnail === `References/Thumbnails/${card.asset.id}.jpg`
    ? `\n\n![[${card.asset.thumbnail}|160]]` : '';
  return `${START}\n<!-- reference-card:${metadata} -->\n${media}${thumbnail}\n${END}`;
}

function replacePlayer(text, card, url) {
  const start = text.indexOf(START), end = text.indexOf(END);
  if (start < 0 || end < start || text.indexOf(START, start + 1) >= 0 || text.indexOf(END, end + 1) >= 0) {
    throw new Error('Player markers changed; preserving this note for manual review');
  }
  return text.slice(0, start) + playerBlock(card, url) + text.slice(end + END.length);
}

const identity = (source, id) => JSON.stringify([source, id]);

function publicationTime(value) {
  if (typeof value === 'number') return value > 0 ? value * 1000 : null;
  if (typeof value !== 'string' || !value.trim()) return null;
  // Normalize explicit source timestamps; never use archive creation time.
  const normalized = /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(value) ? value.replace(' ', 'T') + 'Z' : value;
  const time = Date.parse(normalized);
  return Number.isFinite(time) ? time : null;
}

function library(catalog) {
  const collections = new Map((catalog.collections || []).map(c => [identity(c.source, c.id), c]));
  const posts = new Map(), items = new Map();
  const ensure = key => {
    if (!posts.has(key)) posts.set(key, { key, origins: [], memberships: [], assets: [], published: null });
    return posts.get(key);
  };
  for (const item of catalog.items || []) {
    const post = ensure(item.source_key);
    post.origins.push(item);
    items.set(identity(item.source, item.id), post);
  }
  for (const m of catalog.memberships || []) items.get(identity(m.source, m.item_id))?.memberships.push(m);
  for (const asset of catalog.assets || []) {
    validateAsset(asset);
    for (const origin of asset.origins || []) {
      const post = ensure(origin.source_key);
      if (!post.assets.some(a => a.id === asset.id && a.ordinal === origin.ordinal)) post.assets.push({ ...asset, ordinal: origin.ordinal });
    }
  }
  const acquisitions = new Map((catalog.acquisitions || []).map(a => [a.source_key, a]));
  for (const post of posts.values()) {
    const origins = [...post.origins].sort((a, b) => (a.source === 'instagram' ? 0 : 1) - (b.source === 'instagram' ? 0 : 1));
    post.thumbnail = origins.find(i => i.thumbnail)?.thumbnail;
    post.title = origins.find(i => i.metadata?.title)?.metadata.title || post.key;
    // Older Yaay catalogs called the save's createdAt "source_created". It is
    // not a publication timestamp; only Instagram's taken_at is verified here.
    post.published = origins.filter(i => i.source === 'instagram').map(i => publicationTime(i.metadata?.source_created)).find(t => t !== null) ?? null;
    post.assets.sort((a, b) => a.ordinal - b.ordinal || a.id.localeCompare(b.id));
    post.expected = origins.find(i => i.metadata?.carousel_members?.length)?.metadata.carousel_members || [];
    post.status = acquisitions.get(post.key)?.status || (post.assets.length ? 'unverified' : 'pending');
    post.search = [post.key, ...origins.flatMap(i => [i.id, i.metadata?.title, i.metadata?.caption, i.metadata?.description, i.metadata?.attribution])].filter(Boolean).join(' ').toLocaleLowerCase();
  }
  return { posts: [...posts.values()], collections, sources: catalog.sources || [] };
}

function collectionLabel(lib, source, id) {
  const parts = [], seen = new Set();
  while (id != null && !seen.has(id)) {
    seen.add(id);
    const c = lib.collections.get(identity(source, id));
    if (!c) break;
    parts.unshift(c.title || '(unnamed collection)');
    id = c.parent;
  }
  return [source[0].toUpperCase() + source.slice(1), ...parts].join(' / ');
}

function browse(lib, source, collection, { search = '', order = 'source', history = false } = {}) {
  const matches = m => m.source === source && m.collection_id === collection && Boolean(m.active) !== history;
  const ordinal = p => Math.min(...p.memberships.filter(matches).map(m => m.ordinal));
  return lib.posts.filter(p => p.memberships.some(matches) && p.search.includes(search.trim().toLocaleLowerCase())).sort((a, b) => {
    if (order !== 'source' && a.published !== b.published) {
      if (a.published === null) return 1;
      if (b.published === null) return -1;
      return (a.published - b.published) * (order === 'newest' ? -1 : 1);
    }
    return ordinal(a) - ordinal(b) || a.key.localeCompare(b.key);
  });
}

module.exports = { validateAsset, range, readCard, playerBlock, replacePlayer, library, browse, collectionLabel, publicationTime };
