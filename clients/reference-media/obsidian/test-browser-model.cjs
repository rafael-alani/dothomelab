const { test } = require('node:test');
const assert = require('node:assert/strict');
const { library, browse, collectionLabel } = require('./model.cjs');
const member = (source, collection_id, item_id, ordinal, active = 1) => ({ source, collection_id, item_id, ordinal, active });
const item = (source, id, key, date) => ({ source, id, source_key: key, metadata: { title: key, source_created: date } });
const asset = (n, key, ordinal, source = 'instagram') => ({ id: String(n).repeat(64), path: `objects/${String(n).repeat(64)}.jpg`, created: 999 - n, origins: [{ source, source_key: key, ordinal }] });
function catalog() { return {
  collections: [
    { source: 'instagram', id: 'all', title: 'All Posts', active: 1 },
    { source: 'instagram', id: 'grind', title: 'Grind', active: 1 },
    { source: 'yaay', id: 'grind', title: 'Travel', active: 1 },
    { source: 'yaay', id: 'child', title: 'Cinematic', parent: 'grind', active: 1 },
  ],
  items: [item('instagram', '1', 'instagram:Grind', 300), item('instagram', '2', 'instagram:Samurai', 100), item('yaay', 'alias', 'instagram:Samurai', 100), item('instagram', '3', 'instagram:Pending', 200), item('instagram', '4', 'instagram:Removed', null)],
  memberships: [member('instagram', 'grind', '1', 1), member('instagram', 'grind', '3', 0), member('instagram', 'grind', '4', 2, 0), member('instagram', 'all', '2', 0), member('yaay', 'child', 'alias', 0), member('yaay', 'child', 'alias', 1)],
  assets: [asset(1, 'instagram:Samurai', 1), asset(2, 'instagram:Samurai', 0), asset(3, 'instagram:Grind', 0)],
  acquisitions: [{ source_key: 'instagram:Grind', status: 'archived' }, { source_key: 'instagram:Pending', status: 'retry' }],
}; }
test('exact membership precedes search; pending posts count, historical entries stay separate', () => {
  const lib = library(catalog());
  assert.deepEqual(browse(lib, 'instagram', 'grind').map(p => p.key), ['instagram:Pending', 'instagram:Grind']);
  assert.deepEqual(browse(lib, 'instagram', 'grind', { search: 'Samurai' }), []);
  assert.deepEqual(browse(lib, 'instagram', 'grind', { history: true }).map(p => p.key), ['instagram:Removed']);
  assert.equal(browse(lib, 'instagram', 'grind')[0].status, 'retry');
});
test('one post per cross-source identity, ordered carousel, independent memberships and genuine hierarchy', () => {
  const lib = library(catalog()), post = browse(lib, 'yaay', 'child')[0];
  assert.equal(browse(lib, 'yaay', 'child').length, 1);
  assert.equal(post.origins.length, 2);
  assert.deepEqual(post.assets.map(a => a.id[0]), ['2', '1']);
  assert.equal(post.memberships.length, 3);
  assert.equal(collectionLabel(lib, 'yaay', 'child'), 'Yaay / Travel / Cinematic');
  assert.equal(collectionLabel(lib, 'instagram', 'grind'), 'Instagram / Grind');
});
test('chronology uses publication time, never acquisition time; unknown dates sort last', () => {
  const data = catalog();
  data.items.push(item('yaay', 'legacy', 'yaay:legacy', '2026-11-04 10:00:00'));
  data.memberships.push(member('yaay', 'child', 'legacy', 2));
  const lib = library(data);
  assert.deepEqual(browse(lib, 'instagram', 'grind', { order: 'newest' }).map(p => p.key), ['instagram:Grind', 'instagram:Pending']);
  assert.deepEqual(browse(lib, 'instagram', 'grind', { order: 'oldest' }).map(p => p.key), ['instagram:Pending', 'instagram:Grind']);
  assert.equal(lib.posts.find(p => p.key === 'yaay:legacy').published, null, 'legacy save dates are not publication dates');
  assert.equal(lib.posts.find(p => p.key === 'instagram:Samurai').published, 100000);
});
