const CANONICAL_ORIGIN = 'https://deusagi.ai';
const LEGACY_ORIGIN = 'https://kimbach91-prog.github.io';
const LEGACY_BASE = '/bl-infinity';
const S0_WORK_ITERATIONS = 200000;

export function validateS0Nonce(value) {
  const nonce = String(value || '').trim();
  if (!/^[A-Za-z0-9._:-]{1,64}$/.test(nonce)) throw new Error('BAD_S0_NONCE');
  return nonce;
}

export function computeS0Work(value, iterations = S0_WORK_ITERATIONS) {
  const nonce = validateS0Nonce(value);
  if (!Number.isSafeInteger(iterations) || iterations < 1 || iterations > S0_WORK_ITERATIONS) {
    throw new Error('BAD_S0_ITERATIONS');
  }
  let x = 0x9e3779b9 >>> 0;
  for (let i = 0; i < nonce.length; i++) {
    x = Math.imul((x ^ nonce.charCodeAt(i)) >>> 0, 0x85ebca6b) >>> 0;
    x = (x ^ (x >>> 13)) >>> 0;
  }
  for (let i = 0; i < iterations; i++) {
    x = (Math.imul((x ^ i) >>> 0, 1664525) + 1013904223) >>> 0;
    x = (x ^ (x >>> 16)) >>> 0;
  }
  return x.toString(16).padStart(8, '0');
}

async function computeS0Response(url) {
  const nonce = validateS0Nonce(url.searchParams.get('nonce'));
  const started = Date.now();
  const result = computeS0Work(nonce);
  const elapsedMs = Date.now() - started;
  return Response.json({
    schema: 'deus-cloudflare-s0-compute/1',
    executor: 'CLOUDFLARE_WORKERS',
    data_class: 'S0_PUBLIC',
    nonce,
    iterations: S0_WORK_ITERATIONS,
    result_u32_hex: result,
    elapsed_ms: elapsedMs,
    canonical_write: false,
    protected_payload: false,
    truth: 'BOUNDED_CPU_EXECUTED_NE_GENERAL_CAPACITY_NE_CANONICAL_JOB_DONE'
  }, {
    headers: {
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff',
      'x-deusagi-edge': 'v1',
      'x-deus-executor': 'cloudflare-workers-s0',
      'x-deus-data-class': 'S0'
    }
  });
}

const BLOCKED_PREFIXES = [
  '/.deus', '/.github', '/infra', '/runtime', '/nodes', '/tools',
  '/admin', '/control', '/broker'
];

export function isBlocked(pathname) {
  const p = pathname.toLowerCase();
  return BLOCKED_PREFIXES.some((prefix) => p === prefix || p.startsWith(`${prefix}/`));
}

export function normalizePublicPath(pathname) {
  if (pathname === '/bl-infinity') return '/';
  if (pathname.startsWith('/bl-infinity/')) return pathname.slice('/bl-infinity'.length) || '/';
  return pathname || '/';
}

export function legacyUrlFor(url) {
  const path = normalizePublicPath(url.pathname);
  return new URL(`${LEGACY_BASE}${path}${url.search}`, LEGACY_ORIGIN);
}

export function rewritePublicText(text) {
  return text
    .replaceAll('https://kimbach91-prog.github.io/bl-infinity', CANONICAL_ORIGIN)
    .replaceAll('http://kimbach91-prog.github.io/bl-infinity', CANONICAL_ORIGIN);
}

function publicHeaders(source) {
  const headers = new Headers(source);
  headers.delete('set-cookie');
  headers.set('strict-transport-security', 'max-age=31536000');
  headers.set('x-content-type-options', 'nosniff');
  headers.set('x-frame-options', 'SAMEORIGIN');
  headers.set('referrer-policy', 'strict-origin-when-cross-origin');
  headers.set('permissions-policy', 'camera=(), microphone=(), geolocation=()');
  headers.set('x-deusagi-edge', 'v1');
  return headers;
}

function textual(contentType) {
  return /^(text\/|application\/(json|javascript|xml|rss\+xml|atom\+xml))/i.test(contentType || '');
}

function redirectLocation(location, requestUrl) {
  if (!location) return null;
  try {
    const resolved = new URL(location, LEGACY_ORIGIN);
    if (resolved.hostname === 'kimbach91-prog.github.io' && resolved.pathname.startsWith(LEGACY_BASE)) {
      resolved.protocol = 'https:';
      resolved.hostname = 'deusagi.ai';
      resolved.port = '';
      resolved.pathname = normalizePublicPath(resolved.pathname);
      return resolved.toString();
    }
    return location;
  } catch {
    return location;
  }
}

async function statusResponse() {
  let legacy = { reachable: false, status: null };
  try {
    const probe = await fetch(`${LEGACY_ORIGIN}${LEGACY_BASE}/`, { method: 'HEAD', redirect: 'manual' });
    legacy = { reachable: probe.status >= 200 && probe.status < 500, status: probe.status };
  } catch {
    legacy = { reachable: false, status: null };
  }
  return Response.json({
    system: 'DEUSAGI.AI domain fabric',
    edge: 'cloudflare-worker-v1',
    canonical: CANONICAL_ORIGIN,
    publicOrigin: 'github-pages-legacy',
    protectedCoreExposed: false,
    legacy
  }, {
    status: legacy.reachable ? 200 : 503,
    headers: {
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff',
      'x-deusagi-edge': 'v1'
    }
  });
}

export default {
  async fetch(request) {
    const incoming = new URL(request.url);

    if (incoming.hostname === 'www.deusagi.ai') {
      return Response.redirect(`https://deusagi.ai${incoming.pathname}${incoming.search}`, 308);
    }
    if (incoming.hostname !== 'deusagi.ai') return new Response('Not found', { status: 404 });

    if (incoming.pathname === '/__deusagi/status') return statusResponse();
    if (incoming.pathname === '/__deusagi/compute-s0') {
      if (request.method !== 'GET') {
        return new Response('Method not allowed', { status: 405, headers: { allow: 'GET' } });
      }
      try {
        return await computeS0Response(incoming);
      } catch (error) {
        return Response.json({
          ok: false,
          error: String(error?.message || 'BAD_S0_REQUEST').slice(0, 80),
          canonical_write: false,
          truth: 'S0_COMPUTE_REJECTED'
        }, { status: 400, headers: { 'cache-control': 'no-store' } });
      }
    }

    const normalized = normalizePublicPath(incoming.pathname);
    if (normalized !== incoming.pathname) {
      return Response.redirect(`https://deusagi.ai${normalized}${incoming.search}`, 308);
    }

    if (isBlocked(normalized)) return new Response('Not found', { status: 404 });
    if (!['GET', 'HEAD'].includes(request.method)) {
      return new Response('Method not allowed', { status: 405, headers: { allow: 'GET, HEAD' } });
    }

    const target = legacyUrlFor(incoming);
    const upstream = await fetch(target.toString(), {
      method: request.method,
      redirect: 'manual',
      headers: {
        accept: request.headers.get('accept') || '*/*',
        'accept-language': request.headers.get('accept-language') || 'vi,en;q=0.8',
        'user-agent': 'DEUSAGI-Edge/1.0'
      }
    });

    const headers = publicHeaders(upstream.headers);
    const location = redirectLocation(upstream.headers.get('location'), incoming);
    if (location) headers.set('location', location);

    if (request.method === 'HEAD' || upstream.status === 204 || upstream.status === 304) {
      return new Response(null, { status: upstream.status, headers });
    }

    const contentType = upstream.headers.get('content-type') || '';
    if (textual(contentType)) {
      const text = rewritePublicText(await upstream.text());
      headers.delete('content-length');
      return new Response(text, { status: upstream.status, headers });
    }

    return new Response(upstream.body, { status: upstream.status, headers });
  }
};
