'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const { install } = require('./compat/repairs.cjs');

function fixture(axios = async () => ({ data: { token: 'public-test-token' } })) {
  class Custom {
    getAuthCredentials() { return this.credentials; }
    async authenticate(_image, options) { return { ...options, fallback: true }; }
  }
  class Hub { async getTags() { return ['2.47.2', '2.46.6']; } }
  class Ghcr { async getTags() { return ['6-arm64', '6-amd64', '6', '7']; } }
  install({ Custom, Ghcr, Hub, axios });
  return { Custom, Ghcr, Hub };
}

test('n8n follows upstream stable designation, not numeric beta tags', async () => {
  const { Hub } = fixture(async request => {
    assert.equal(request.url, 'https://api.github.com/repos/n8n-io/n8n/releases/latest');
    return { data: { tag_name: 'n8n@2.46.6', prerelease: false, draft: false } };
  });
  const provider = new Hub();
  assert.deepEqual(await provider.getTags({ name: 'n8nio/n8n' }), ['2.46.6']);
  assert.deepEqual(await provider.getTags({ name: 'other/image' }), ['2.47.2', '2.46.6']);
});

test('n8n fails closed on invalid release metadata and rate limits', async () => {
  for (const data of [
    { tag_name: 'n8n@2.47.2', prerelease: true, draft: false },
    { tag_name: 'n8n@2.47.2', prerelease: false, draft: true },
    { tag_name: 'not-a-release', prerelease: false, draft: false },
  ]) {
    const { Hub } = fixture(async () => ({ data }));
    await assert.rejects(new Hub().getTags({ name: 'n8nio/n8n' }), /stable release metadata/);
  }
  const { Hub } = fixture(async () => { throw { response: { status: 429 }, secret: 'hidden' }; });
  await assert.rejects(new Hub().getTags({ name: 'n8nio/n8n' }), /^Error: n8n stable release lookup failed: 429$/);
});

test('retained cross-seed stays on its multi-platform major tag', async () => {
  const { Ghcr } = fixture();
  const provider = new Ghcr();
  assert.deepEqual(await provider.getTags({ name: 'cross-seed/cross-seed', tag: { value: '6' } }), ['6']);
  assert.equal((await provider.getTags({ name: 'other/image', tag: { value: '6' } })).length, 4);
});

test('public providers acquire pull-only tokens and preserve registry request headers', async () => {
  const requests = [];
  const { Custom } = fixture(async request => {
    requests.push(request);
    return { data: { token: 'public-test-token', expires_in: 300 } };
  });
  for (const url of ['https://lscr.io', 'https://registry.gitlab.com']) {
    const provider = new Custom(); provider.configuration = { url };
    const options = { headers: { Accept: 'manifest' } };
    const response = await provider.authenticate({ name: 'test/image' }, options);
    await provider.authenticate({ name: 'test/image' }, options);
    assert.equal(response.headers.Authorization, 'Bearer public-test-token');
    assert.equal(response.headers.Accept, 'manifest');
    assert.equal(options.headers.Authorization, undefined);
  }
  assert.equal(requests.length, 2);
  assert.ok(requests.every(request => request.params.scope === 'repository:test/image:pull'));
  assert.ok(requests.every(request => !request.headers.Authorization));
});

test('unrelated and authenticated custom registries keep existing authentication', async () => {
  const { Custom } = fixture(async () => { throw new Error('must not request token'); });
  const provider = new Custom(); provider.configuration = { url: 'https://private.example' };
  assert.equal((await provider.authenticate({}, {})).fallback, true);
  provider.configuration.url = 'https://lscr.io'; provider.credentials = 'existing';
  assert.equal((await provider.authenticate({}, {})).fallback, true);
});

test('token failures are surfaced without logging axios objects', async () => {
  const { Custom } = fixture(async () => { throw { response: { status: 429 }, secret: 'hidden' }; });
  const provider = new Custom(); provider.configuration = { url: 'https://lscr.io' };
  await assert.rejects(provider.authenticate({ name: 'n8nio/n8n' }, {}), /^Error: Public registry token request failed: 429$/);
});
