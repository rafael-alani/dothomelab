'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const { install } = require('./compat/repairs.cjs');

function fixture(axios = async () => ({ data: { token: 'public-test-token' } })) {
  class Custom {
    getAuthCredentials() { return this.credentials; }
    async authenticate(_image, options) { return { ...options, fallback: true }; }
  }
  class Ghcr { async getTags() { return ['6-arm64', '6-amd64', '6', '7']; } }
  class Docker {}
  install({ Custom, Ghcr, Docker, axios });
  return { Custom, Ghcr, Docker };
}

test('public providers acquire pull-only tokens and preserve registry request headers', async () => {
  const requests = [];
  const { Custom } = fixture(async request => {
    requests.push(request);
    return { data: { token: 'public-test-token', expires_in: 300 } };
  });
  for (const url of ['https://lscr.io', 'https://registry.gitlab.com', 'https://docker.n8n.io']) {
    const provider = new Custom(); provider.configuration = { url };
    const options = { headers: { Accept: 'manifest' } };
    const response = await provider.authenticate({ name: 'test/image' }, options);
    await provider.authenticate({ name: 'test/image' }, options);
    assert.equal(response.headers.Authorization, 'Bearer public-test-token');
    assert.equal(response.headers.Accept, 'manifest');
    assert.equal(options.headers.Authorization, undefined);
  }
  assert.equal(requests.length, 3);
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
  const provider = new Custom(); provider.configuration = { url: 'https://docker.n8n.io' };
  await assert.rejects(provider.authenticate({ name: 'n8nio/n8n' }, {}), /^Error: Public registry token request failed: 429$/);
});

test('cross-seed remains on its multi-platform major channel', async () => {
  const { Ghcr } = fixture(); const provider = new Ghcr();
  assert.deepEqual(await provider.getTags({ name: 'cross-seed/cross-seed', tag: { value: '6' } }), ['6']);
  assert.equal((await provider.getTags({ name: 'other/image', tag: { value: '6' } })).length, 4);
});

for (const failure of ['callback', 'event', 'success']) {
  test(`Docker pull ${failure} is handled before replacement can proceed`, async () => {
    const { Docker } = fixture(); const provider = new Docker();
    let replaced = false; const logs = [];
    const api = {
      pull: async () => 'stream',
      modem: { followProgress: (_stream, done) => done(
        failure === 'callback' ? new Error('no space left on device') : null,
        failure === 'event' ? [{ errorDetail: { message: 'pull denied' } }] : [],
      ) },
    };
    const trigger = async () => {
      await provider.pullImage(api, undefined, 'example:latest', { info: line => logs.push(line) });
      replaced = true;
    };
    if (failure === 'success') {
      await trigger(); assert.equal(replaced, true);
    } else {
      await assert.rejects(trigger()); assert.equal(replaced, false);
      assert.ok(!logs.some(line => line.includes('with success')));
    }
  });
}
