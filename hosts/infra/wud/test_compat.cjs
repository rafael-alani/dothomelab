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
  class Docker {
    cloneContainer(current, image) {
      const result = { ...current.Config, Image: image,
        HostConfig: current.HostConfig,
        NetworkingConfig: { EndpointsConfig: current.NetworkSettings.Networks } };
      // Match the pinned upstream method's mutation of the inspected input.
      for (const endpoint of Object.values(result.NetworkingConfig.EndpointsConfig || {})) {
        if (endpoint.Aliases) endpoint.Aliases = endpoint.Aliases.filter(alias => !current.Id.startsWith(alias));
      }
      return result;
    }
  }
  install({ Custom, Ghcr, Docker, axios });
  return { Custom, Ghcr, Docker };
}

test('replacement drops generated MACs while retaining static IPAM and the original inspection', () => {
  const { Docker } = fixture();
  const current = { Id: 'abcdef123456789', Config: { MacAddress: '02:42:ac:13:00:05' },
    HostConfig: { NetworkMode: 'example' }, NetworkSettings: { Networks: {
      example: { MacAddress: '02:42:ac:13:00:05', Aliases: ['app', 'abcdef123456'],
        IPAMConfig: { IPv4Address: '172.19.0.2' } },
    } } };
  const before = structuredClone(current);
  const result = new Docker().cloneContainer(current, 'new:image');
  assert.equal(result.MacAddress, undefined);
  assert.equal(result.NetworkingConfig.EndpointsConfig.example.MacAddress, undefined);
  assert.deepEqual(result.NetworkingConfig.EndpointsConfig.example.IPAMConfig, { IPv4Address: '172.19.0.2' });
  assert.deepEqual(result.NetworkingConfig.EndpointsConfig.example.Aliases, ['app']);
  assert.deepEqual(current, before);
});

test('replacement retains custom MACs and handles host/container network modes', () => {
  const { Docker } = fixture();
  for (const mode of ['host', 'container:shared', 'bridge']) {
    const current = { Id: 'abcdef', Config: { MacAddress: '02:ab:cd:00:00:01' },
      HostConfig: { NetworkMode: mode }, NetworkSettings: { Networks: {
        custom: { MacAddress: '02:ab:cd:00:00:01' },
      } } };
    const result = new Docker().cloneContainer(current, 'new:image');
    assert.equal(result.MacAddress, current.Config.MacAddress);
    assert.equal(result.NetworkingConfig.EndpointsConfig.custom.MacAddress, current.Config.MacAddress);
    assert.equal(result.HostConfig.NetworkMode, mode);
  }
  const result = new Docker().cloneContainer({ Id: 'id', Config: {}, HostConfig: {}, NetworkSettings: {} }, 'image');
  assert.equal(result.Image, 'image');
});

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
