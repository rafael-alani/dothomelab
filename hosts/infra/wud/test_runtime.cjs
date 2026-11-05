'use strict';
// Run inside the pinned WUD image, without a network or Docker socket.
const assert = require('node:assert/strict');
const test = require('node:test');
const root = '/home/node/app/dist';
const Docker = require(`${root}/triggers/providers/docker/Docker`).default;
const Custom = require(`${root}/registries/providers/custom/Custom`).default;

test('native registry authentication follows an anonymous bearer challenge', async () => {
  const provider = Object.create(Custom.prototype);
  provider.configuration = { url: 'https://registry.invalid' };
  provider.getAuthCredentials = () => undefined;
  provider.getCachedBearerToken = () => undefined;
  provider.getBearerChallenge = async () => ({ realm: 'https://auth.invalid/token' });
  let exchanged = false;
  provider.getBearerToken = async (_image, url, credentials, challenge) => {
    assert.equal(url, provider.configuration.url);
    assert.equal(credentials, undefined);
    assert.equal(challenge.realm, 'https://auth.invalid/token');
    exchanged = true;
    return 'test-only-token';
  };
  const result = await provider.authenticate({ name: 'test/image' }, { headers: { Accept: 'manifest' } });
  assert.ok(exchanged);
  assert.equal(result.headers.Authorization, 'Bearer test-only-token');
  assert.equal(result.headers.Accept, 'manifest');
});

test('native replacement removes derived MACs and preserves a configured custom MAC', () => {
  const trigger = Object.create(Docker.prototype);
  trigger.getFullyQualifiedImage = () => 'example:new';
  const source = { Id: 'abcdef1234', Name: '/example', Config: { MacAddress: '02:42:ac:13:00:05' },
    HostConfig: {}, NetworkSettings: { Networks: {
      app: { IPAddress: '172.19.0.5', MacAddress: '02:42:ac:13:00:05', Aliases: ['example', 'abcdef'] },
      custom: { IPAddress: '172.20.0.5', MacAddress: '02:ab:cd:00:00:01' },
    } } };
  const result = trigger.cloneContainer(source, {});
  assert.equal(result.MacAddress, undefined);
  assert.equal(result.NetworkingConfig.EndpointsConfig.app.MacAddress, undefined);
  assert.equal(result.NetworkingConfig.EndpointsConfig.custom.MacAddress, '02:ab:cd:00:00:01');
});

for (const failure of ['callback', 'event', 'success']) {
  test(`native pull ${failure} is propagated before replacement`, async () => {
    const trigger = Object.create(Docker.prototype);
    const log = { info() {}, warn() {}, debug() {} };
    const docker = { pull: async () => 'stream', modem: { followProgress: (_stream, done) =>
      done(failure === 'callback' ? new Error('failed') : null,
        failure === 'event' ? [{ errorDetail: { message: 'failed' } }] : []) } };
    if (failure === 'success') await trigger.pullImageOnce(docker, undefined, 'example:new', log);
    else await assert.rejects(trigger.pullImageOnce(docker, undefined, 'example:new', log));
  });
}
