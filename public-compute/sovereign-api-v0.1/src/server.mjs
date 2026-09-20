import http from 'node:http';
import { compileExternalProjection, makeEliteReceipt, qualifyElitePacket } from './elite-packet.mjs';
import { planTransportRoute, publicProviderRegistry } from './provider-registry.mjs';

function json(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    'content-length': Buffer.byteLength(data)
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

export function createSovereignApiServer({ routerMetricsResolver, replayStore } = {}) {
  const seenIdempotency = replayStore?.idempotency ?? new Set();
  const seenDigests = replayStore?.digests ?? new Set();

  return http.createServer(async (req, res) => {
    try {
      if (req.method === 'GET' && req.url === '/v1/status') {
        return json(res, 200, {
          service: 'DEUS_SOVEREIGN_API',
          version: '0.1',
          state: process.env.DEUS_RUNTIME_STATE || 'SOURCE_CANDIDATE',
          source_revision: process.env.DEUS_SOURCE_REV || null,
          external_default_classes: ['S0', 'S1'],
          mang: 'ENFORCED_BY_GATE_SOURCE',
          zero_model_fast_path: true,
          free_inference_guaranteed: false,
          openai: {
            placement: 'FIRST_REGISTERED_PROVIDER_CAPABILITY',
            runtime_canary_verified: false
          },
          provider_execution: false,
          canonical_write: false
        });
      }

      if (req.method === 'GET' && req.url === '/v1/providers') {
        return json(res, 200, {
          providers: publicProviderRegistry(),
          truth_boundary: 'Registry state is source/control-plane metadata, not proof of runtime provider execution.'
        });
      }

      if (req.method === 'POST' && req.url === '/v1/routes/plan') {
        const body = await readJson(req);
        const plan = planTransportRoute({
          requires_inference: Boolean(body.requires_inference),
          preferred_provider: body.preferred_provider ?? null,
          data_class: body.data_class ?? 'S0',
          operation: body.operation ?? 'PACKET_EXCHANGE'
        });
        return json(res, plan.state === 'READY' ? 200 : 422, { plan });
      }

      if (req.method === 'POST' && (req.url === '/v1/packets/qualify' || req.url === '/v1/handshake')) {
        const body = await readJson(req);
        const packet = body.packet ?? body;
        const routerMetrics = routerMetricsResolver
          ? await routerMetricsResolver(packet, req)
          : body.router_metrics;
        const decision = qualifyElitePacket(packet, {
          router_metrics: routerMetrics,
          seen_idempotency_keys: seenIdempotency,
          seen_packet_digests: seenDigests
        });

        const receipt = makeEliteReceipt({ packet, decision, observed: { endpoint: req.url } });
        if (decision.state !== 'ACCEPT') return json(res, 422, { decision, receipt });

        const projection = compileExternalProjection(packet);
        seenIdempotency.add(packet.idempotency_key);
        seenDigests.add(decision.packet_digest);
        return json(res, 202, {
          decision,
          projection,
          receipt,
          next: req.url === '/v1/handshake' ? 'NEGOTIATE_BOUNDED_EXCHANGE' : 'ROUTE_BY_CAPABILITY'
        });
      }

      return json(res, 404, { error: 'NOT_FOUND' });
    } catch (error) {
      const code = error?.message === 'BODY_TOO_LARGE' ? 413 : 400;
      return json(res, code, { error: error?.message || 'BAD_REQUEST' });
    }
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = Number(process.env.PORT || 8787);
  const host = process.env.HOST || '0.0.0.0';
  createSovereignApiServer().listen(port, host, () => {
    process.stdout.write(`DEUS Sovereign API source candidate listening on ${host}:${port}\n`);
  });
}
