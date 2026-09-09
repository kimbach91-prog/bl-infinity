import https from 'node:https';
import http from 'node:http';
import { readFileSync } from 'node:fs';
import crypto from 'node:crypto';

const certFile = process.env.BL_MTLS_CERT_FILE;
const keyFile = process.env.BL_MTLS_KEY_FILE;
const caFile = process.env.BL_MTLS_CA_FILE;
if (!certFile || !keyFile || !caFile) throw new Error('BL_MTLS_CERT_FILE, BL_MTLS_KEY_FILE and BL_MTLS_CA_FILE are required');

const host = process.env.BL_MTLS_HOST || '127.0.0.1';
const port = Number(process.env.BL_MTLS_PORT || 9443);
const upstreamHost = '127.0.0.1';
const upstreamPort = Number(process.env.BL_CONTROL_INTERNAL_PORT || 8787);
const maxBody = Number(process.env.BL_MTLS_MAX_BODY_BYTES || 65536);
const allow = new Set([
  'POST /providers/heartbeat/self',
  'GET /health'
]);

function certIdentity(socket) {
  if (!socket.authorized) throw new Error('CLIENT_CERT_UNAUTHORIZED');
  const cert = socket.getPeerCertificate(true);
  if (!cert?.raw) throw new Error('CLIENT_CERT_MISSING');
  return {
    subject: cert.subject?.CN || null,
    issuer: cert.issuer?.CN || null,
    serialNumber: cert.serialNumber || null,
    fingerprint256: crypto.createHash('sha256').update(cert.raw).digest('hex')
  };
}

function collect(req) {
  return new Promise((resolve, reject) => {
    const chunks = []; let size = 0;
    req.on('data', (chunk) => { size += chunk.length; if (size > maxBody) { reject(new Error('BODY_TOO_LARGE')); req.destroy(); return; } chunks.push(chunk); });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

const server = https.createServer({
  cert: readFileSync(certFile),
  key: readFileSync(keyFile),
  ca: readFileSync(caFile),
  requestCert: true,
  rejectUnauthorized: true,
  minVersion: 'TLSv1.3',
  honorCipherOrder: true
}, async (req, res) => {
  try {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    const route = `${req.method} ${req.url}`;
    if (!allow.has(route)) { res.writeHead(404); return res.end(); }
    const identity = certIdentity(req.socket);
    const payload = await collect(req);
    const headers = { ...req.headers };
    delete headers.host;
    delete headers.connection;
    headers['x-bl-mtls-fingerprint'] = identity.fingerprint256;
    headers['x-bl-mtls-subject'] = identity.subject || '';
    headers['x-bl-mtls-serial'] = identity.serialNumber || '';
    headers['content-length'] = String(payload.length);
    const upstream = http.request({ host: upstreamHost, port: upstreamPort, path: req.url, method: req.method, headers }, (up) => {
      res.writeHead(up.statusCode || 502, up.headers);
      up.pipe(res);
    });
    upstream.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end(); });
    upstream.end(payload);
  } catch (error) {
    if (!res.headersSent) res.writeHead(error.message === 'BODY_TOO_LARGE' ? 413 : 403, { 'content-type': 'application/json', 'cache-control': 'no-store' });
    res.end(JSON.stringify({ error: error.message, failClosed: true }));
  }
});

server.listen(port, host, () => {
  console.log(JSON.stringify({ service: 'bl-mtls-node-ingress', host, port, tls: '1.3', requestCert: true, rejectUnauthorized: true, allow: [...allow] }));
});
