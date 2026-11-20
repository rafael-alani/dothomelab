import http from 'node:http';
import net from 'node:net';
import { fileURLToPath } from 'node:url';

export function createGateway({ socketPath = '/run/branchline-preview/runner.sock', targetHost = '192.168.0.114' } = {}) {

async function target(req) {
  const match = /^bl-(\d{5})\.staging\.rafael\.media(?::443)?$/.exec(req.headers.host || '');
  if (!match) throw new Error('Unknown preview hostname');
  const port = Number(match[1]);
  const state = await new Promise((resolve, reject) => {
    const request = http.get({ socketPath, path: '/state', timeout: 3000 }, response => {
      const chunks = [];
      response.on('data', chunk => chunks.push(chunk));
      response.on('end', () => { try { resolve(JSON.parse(Buffer.concat(chunks))); } catch (error) { reject(error); } });
    });
    request.on('timeout', () => request.destroy(new Error('Runner timeout')));
    request.on('error', reject);
  });
  if (!state.environments?.some(env => env.port === port && ['ready', 'running', 'starting'].includes(env.status))) {
    throw new Error('Preview is not running');
  }
  return port;
}

const server = http.createServer(async (req, res) => {
  try {
    const port = await target(req);
    const proxy = http.request({ hostname: targetHost, port, path: req.url, method: req.method,
      headers: { ...req.headers, 'x-forwarded-proto': 'https' } }, response => {
      res.writeHead(response.statusCode, response.headers); response.pipe(res);
    });
    proxy.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end('Preview unavailable'); });
    req.on('aborted', () => proxy.destroy());
    req.pipe(proxy);
  } catch {
    res.writeHead(503, { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store' });
    res.end('This preview is not running. Open Branchline to start it.');
  }
});
server.on('upgrade', async (req, socket, head) => {
  try {
    const port = await target(req);
    const upstream = net.connect(port, targetHost, () => {
      upstream.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n`);
      for (const [key, value] of Object.entries(req.headers)) upstream.write(`${key}: ${value}\r\n`);
      upstream.write('\r\n'); if (head.length) upstream.write(head);
      socket.pipe(upstream).pipe(socket);
    });
    upstream.on('error', () => socket.destroy());
    socket.on('error', () => upstream.destroy());
    socket.on('close', () => upstream.destroy());
  } catch { socket.end('HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\n\r\n'); }
});
return server;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) createGateway().listen(8087, '192.168.0.114');
