const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validateAsset, range, playerBlock, replacePlayer, readCard } = require('./model.cjs');
const asset = { id: 'a'.repeat(64), path: 'objects/' + 'a'.repeat(64) + '.mp4', title: 'Fixture' };
test('reject traversal and invalid excerpt boundaries', () => {
  assert.throws(() => validateAsset({ ...asset, path: '../private.mp4' }));
  for (const v of [[-1, 3, 10], [4, 3, 10], [0, 11, 10], [0, NaN, 10]]) assert.throws(() => range(...v));
  assert.deepEqual(range(3, 7, 24), { start: 3, end: 7 });
});
test('independent project edits retain annotations and the immutable original', () => {
  const a = { asset, start: 3, end: 7, loop: false }, b = { asset, start: 12, end: 18, loop: true };
  const first = 'My heading\n' + playerBlock(a, 'file:///archive/a.mp4') + '\nMy annotation';
  const second = 'Second project\n' + playerBlock(b, 'file:///archive/a.mp4');
  const updated = replacePlayer(first, { ...a, end: 6 }, 'file:///archive/a.mp4');
  assert.equal(readCard(updated).end, 6); assert.equal(readCard(second).end, 18);
  assert.ok(updated.startsWith('My heading\n')); assert.ok(updated.endsWith('\nMy annotation'));
  assert.equal(readCard(updated).asset.id, readCard(second).asset.id);
  assert.throws(() => replacePlayer('user removed marker', a, 'file:///archive/a.mp4'));
});
