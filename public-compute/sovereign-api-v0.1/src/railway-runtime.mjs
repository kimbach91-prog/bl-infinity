import http from 'node:http';
import crypto from 'node:crypto';
import { compileExternalProjection, makeEliteReceipt, qualifyElitePacket } from './elite-packet.mjs';
import { planTransportRoute, publicProviderRegistry } from './provider-registry.mjs';

const PORT = Number(process.env.PORT || 8080);
const HOST = '0.0.0.0';
const SOURCE_REV = process.env.DEUS_SOURCE_REV || '48ae7811a74eb9dc9b954c40970b3427ea64f10a';
const MIRROR_REV = process.env.DEUS_MIRROR_REV || '6f4639095cbe265c14317974fa95b171795ad859';
const BOOT_EPOCH_MS = Date.now();
const BOOT_ID = crypto.createHash('sha256').update(`RAILWAY:${BOOT_EPOCH_MS}`).digest('hex').slice(0, 24);
const seenIdempotency = new Set();
const seenDigests = new Set();
let seq = 0;
let lastHeartbeat = new Date().toISOString();

function fenceToken() {
  return crypto.createHash('sha256').update(`RAILWAY:${BOOT_EPOCH_MS}:${seq}`).digest('hex');
}

function controlState() {
  return {
    provider: 'RAILWAY',
    role: 'PROVIDER_NATIVE_S0_CONTROLLER',
    boot_id: BOOT_ID,
    boot_epoch_ms: BOOT_EPOCH_MS,
    seq,
    fence_epoch: BOOT_EPOCH_MS,
    fence_token: fenceToken(),
    last_heartbeat_utc: lastHeartbeat,
    lease_until_utc: new Date(Date.now() + 45_000).toISOString(),
    source_revision: SOURCE_REV,
    mirror_revision: MIRROR_REV,
    canonical_write: false,
    execution_authority: false
  };
}

function heartbeat() {
  seq += 1;
  lastHeartbeat = new Date().toISOString();
  console.log(JSON.stringify({ event: 'deus_controller_heartbeat', ...controlState() }));
}

setInterval(heartbeat, 15_000).unref();

function json(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(data),
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff'
  });
  res.end(data);
}

async function readJson(req, limit = 32_000) {
  let size = 0;
  const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > limit) throw new Error('BODY_TOO_LARGE');
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || '/', 'http://localhost');

    if (req.method === 'GET' && (url.pathname === '/healthz' || url.pathname === '/v1/status')) {
      return json(res, 200, {
        service: 'DEUS_SOVEREIGN_API',
        version: '0.1-railway',
        state: 'RAILWAY_LIVE_S0',
        source_revision: SOURCE_REV,
        mirror_revision: MIRROR_REV,
        external_default_classes: ['S0', 'S1'],
        mang: 'ENFORCED_BY_GATE_SOURCE',
        zero_model_fast_path: true,
        provider_execution: false,
        canonical_write: false,
        controller: controlState()
      });
    }

    if (req.method === 'GET' && url.pathname === '/v1/providers') {
      return json(res, 200, {
        providers: publicProviderRegistry(),
        truth_boundary: 'Registry metadata is not provider execution proof.'
      });
    }

    if (req.method === 'GET' && url.pathname === '/v1/control-state') {
      return json(res, 200, controlState());
    }

    if (req.method === 'POST' && url.pathname === '/v1/control/validate') {
      const body = await readJson(req);
      const current = controlState();
      if (body.fence_token === current.fence_token) {
        return json(res, 200, { state: 'CURRENT_FENCE', control: current });
      }
      return json(res, 409, { state: 'STALE_FENCE_REJECTED', current });
    }

    if (req.method === 'POST' && url.pathname === '/v1/routes/plan') {
      const body = await readJson(req);
      const plan = planTransportRoute({
        requires_inference: Boolean(body.requires_inference),
        preferred_provider: body.preferred_provider ?? null,
        data_class: body.data_class ?? 'S0',
        operation: body.operation ?? 'PACKET_EXCHANGE'
      });
      return json(res, plan.state === 'READY' ? 200 : 422, { plan });
    }

    if (req.method === 'POST' && (url.pathname === '/v1/handshake' || url.pathname === '/v1/packets/qualify')) {
      const body = await readJson(req);
      const packet = body.packet ?? body;
      const decision = qualifyElitePacket(packet, {
        router_metrics: body.router_metrics,
        seen_idempotency_keys: seenIdempotency,
        seen_packet_digests: seenDigests
      });
      const receipt = makeEliteReceipt({
        packet,
        decision,
        route: 'DEUS_RAILWAY_SOVEREIGN_API_V0_1',
        observed: { endpoint: url.pathname, provider: 'RAILWAY', boot_id: BOOT_ID }
      });
      if (decision.state !== 'ACCEPT') return json(res, 422, { decision, receipt });

      seenIdempotency.add(packet.idempotency_key);
      seenDigests.add(decision.packet_digest);
      return json(res, 202, {
        decision,
        projection: compileExternalProjection(packet),
        receipt,
        next: url.pathname === '/v1/handshake' ? 'NEGOTIATE_BOUNDED_EXCHANGE' : 'ROUTE_BY_CAPABILITY'
      });
    }

    return json(res, 404, { error: 'NOT_FOUND' });
  } catch (error) {
    return json(res, error?.message === 'BODY_TOO_LARGE' ? 413 : 400, { error: error?.message || 'BAD_REQUEST' });
  }
});

server.listen(PORT, HOST, () => {
  console.log(JSON.stringify({ event: 'service_ready', provider: 'RAILWAY', port: PORT, ...controlState() }));
});
