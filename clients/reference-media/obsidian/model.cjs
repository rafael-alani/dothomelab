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
  return `${START}\n<!-- reference-card:${metadata} -->\n${media}\n${END}`;
}

function replacePlayer(text, card, url) {
  const start = text.indexOf(START), end = text.indexOf(END);
  if (start < 0 || end < start || text.indexOf(START, start + 1) >= 0 || text.indexOf(END, end + 1) >= 0) {
    throw new Error('Player markers changed; preserving this note for manual review');
  }
  return text.slice(0, start) + playerBlock(card, url) + text.slice(end + END.length);
}

module.exports = { validateAsset, range, readCard, playerBlock, replacePlayer };
