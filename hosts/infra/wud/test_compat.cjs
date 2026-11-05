'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const { install } = require('./compat/repairs.cjs');

test('retained cross-seed stays on its multi-platform major tag', async () => {
  class Ghcr { async getTags() { return ['6-arm64', '6-amd64', '6', '7']; } }
  install({ Ghcr });
  const provider = new Ghcr();
  assert.deepEqual(await provider.getTags({ name: 'cross-seed/cross-seed', tag: { value: '6' } }), ['6']);
  assert.equal((await provider.getTags({ name: 'other/image', tag: { value: '6' } })).length, 4);
});
