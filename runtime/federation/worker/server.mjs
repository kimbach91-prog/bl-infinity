import http from 'node:http';
import { ReplayGuard, verifyWorkerEnvelope } from '../lib/protocol.mjs';
import { createProviderHeartbeatClientFromEnv } from './heartbeat.mjs';
import { safeDefaultHandlers } from './handlers.mjs';

export function createWorkerServer({ handlers = safeDefaultHandlers, sharedSecret = process.env.BL_FEDERATION_SHARED_SECRET, requireAuth = true, maxConcurrency = Number(process.env.BL_WORKER_MAX_CONCURRENCY || 2), maxBodyBytes = Number(process.env.BL_WORKER_MAX_BODY_BYTES || 1_048_576) } = {}) {
  const handlerMap = handlers instanceof Map ? handlers : new Map(Object.entries(handlers));
  const replayGuard = new ReplayGuard();
  let inFlight = 0;
  const completed = new Map();
  const maxCompleted = Number(process.env.BL_WORKER_IDEMPOTENCY_ENTRIES || 10000);
  const server = http.createServer(async (req, res) => {
    setJson(res);
    if (req.method === 'GET' && req.url === '/health') return send(res, 200, { ok: true, service: 'bl-federation-worker', inFlight, maxConcurrency });
    if (req.method === 'GET' && req.url === '/v1/capabilities') return send(res, 200, { capabilities: [...handlerMap.keys()].sort() });
    if (req.method !== 'POST' || req.url !== '/v1/execute') return send(res, 404, { error: 'not found' });
    if (inFlight >= maxConcurrency) return send(res, 429, { error: 'worker concurrency limit reached' });
    let body; try { body = await readBody(req, maxBodyBytes); } catch (error) { return send(res, error.code === 'BODY_TOO_LARGE' ? 413 : 400, { error: error.message }); }
    if (requireAuth) { if (!sharedSecret) return send(res, 503, { error: 'worker auth is not configured' }); const verdict = verifyWorkerEnvelope(sharedSecret, req.headers, body, { replayGuard }); if (!verdict.ok) return send(res, 401, { error: verdict.reason }); }
    let envelope; try { envelope = JSON.parse(body || '{}'); } catch { return send(res, 400, { error: 'invalid JSON' }); }
    const task = envelope.task;
    if (!task?.id || !task?.capability) return send(res, 400, { error: 'task.id and task.capability are required' });
    const handler = handlerMap.get(task.capability); if (!handler) return send(res, 403, { error: 'capability not installed' });
    const idemKey = task.idempotencyKey ?? task.id;
    const prior = completed.get(idemKey);
    if (prior) { if (prior.capability !== task.capability) return send(res, 409, { error: 'idempotency key reused for different capability' }); return send(res, 200, { ok: true, taskId: task.id, result: structuredClone(prior.result), idempotentReplay: true }); }
    if (task.deadlineAt && Date.parse(task.deadlineAt) <= Date.now()) return send(res, 408, { error: 'task deadline expired' });
    inFlight += 1;
    try {
      const result = await handler(structuredClone(task.payload), { task: structuredClone(task) });
      if (completed.size >= maxCompleted && !completed.has(idemKey)) completed.delete(completed.keys().next().value);
      completed.set(idemKey, { capability: task.capability, result: structuredClone(result) });
      return send(res, 200, { ok: true, taskId: task.id, result });
    } catch (error) { return send(res, 500, { error: error.message }); }
    finally { inFlight -= 1; }
  });
  server.getFederationState = () => ({ inFlight, maxConcurrency, capabilities: [...handlerMap.keys()].sort() });
  return server;
}

export function startWorkerFromEnv() {
  const port = Number(process.env.PORT || 8790), host = process.env.HOST || '127.0.0.1';
  const server = createWorkerServer();
  let heartbeat = null;
  server.listen(port, host, () => {
    console.log(`BL federation worker listening on http://${host}:${port}`);
    try {
      heartbeat = createProviderHeartbeatClientFromEnv({ getInFlight: () => server.getFederationState().inFlight });
      if (heartbeat) {
        heartbeat.start();
        console.log('BL federation worker heartbeat enabled');
      }
    } catch (error) {
      console.error(`BL federation worker heartbeat configuration failed: ${error.message}`);
      process.exitCode = 1;
      server.close();
    }
  });
  server.once('close', () => heartbeat?.stop());
  return server;
}

async function readBody(req, maxBytes) { let size = 0; const chunks = []; for await (const chunk of req) { size += chunk.length; if (size > maxBytes) { const error = new Error('request body too large'); error.code = 'BODY_TOO_LARGE'; throw error; } chunks.push(chunk); } return Buffer.concat(chunks).toString('utf8'); }
function setJson(res) { res.setHeader('content-type', 'application/json; charset=utf-8'); res.setHeader('cache-control', 'no-store'); }
function send(res, status, body) { res.statusCode = status; res.end(JSON.stringify(body)); }
if (import.meta.url === `file://${process.argv[1]}`) startWorkerFromEnv();
