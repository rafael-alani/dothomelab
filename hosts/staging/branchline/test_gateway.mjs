import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { once } from 'node:events';
import { test } from 'node:test';
import { createGateway } from './gateway.mjs';

const listen = async (server, address = 0) => { server.listen(address, typeof address === 'number' ? '127.0.0.1' : undefined); await once(server, 'listening'); return server; };
const close = server => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); });
const request = (port, host, route = '/') => new Promise((resolve, reject) => {
  const req = http.get({ hostname: '127.0.0.1', port, path: route, headers: { Host: host } }, res => {
    let body = ''; res.on('data', chunk => body += chunk); res.on('end', () => resolve({ status: res.statusCode, body }));
  }); req.on('error', reject);
});

test('private gateway routes only a registered active preview and preserves path/query', async t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'branchline-gateway-')); t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const upstream = await listen(http.createServer((req, res) => res.end(JSON.stringify({ url: req.url, protocol: req.headers['x-forwarded-proto'] }))));
  let state = { environments: [{ port: upstream.address().port, status: 'ready' }] };
  const socketPath = path.join(directory, 'runner.sock');
  const runner = await listen(http.createServer((req, res) => { assert.equal(req.url, '/state'); res.end(JSON.stringify(state)); }), socketPath);
  const gateway = await listen(createGateway({ socketPath, targetHost: '127.0.0.1' }));
  t.after(async () => { await close(gateway); await close(runner); await close(upstream); });
  const host = `bl-${upstream.address().port}.staging.rafael.media`;
  const good = await request(gateway.address().port, host, '/programme?track=52');
  assert.equal(good.status, 200); assert.deepEqual(JSON.parse(good.body), { url: '/programme?track=52', protocol: 'https' });
  for (const hostile of ['localhost', 'branchline.staging.rafael.media', host + '.attacker.example', 'bl-00022.staging.rafael.media']) {
    assert.equal((await request(gateway.address().port, hostile)).status, 503);
  }
  state.environments[0].status = 'stopped'; assert.equal((await request(gateway.address().port, host)).status, 503);
  state.environments[0].status = 'starting'; assert.equal((await request(gateway.address().port, host + ':443')).status, 200);
  state = { environments: [] }; assert.equal((await request(gateway.address().port, host)).status, 503);
});
