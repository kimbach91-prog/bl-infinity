import { createNonce, signWorkerEnvelope } from './protocol.mjs';

export async function buildTransportHeaders(provider, body, env = process.env) {
  const headers = { 'content-type': 'application/json' };
  const auth = provider.transport?.auth ?? 'none';
  if (auth === 'hmac-env') {
    const secret = env[provider.transport?.secretEnv];
    if (!secret) throw new Error(`missing HMAC secret env for provider ${provider.id}`);
    const timestamp = Date.now(); const nonce = createNonce();
    headers['x-bl-timestamp'] = String(timestamp); headers['x-bl-nonce'] = nonce; headers['x-bl-signature'] = signWorkerEnvelope(secret, { timestamp, nonce, body });
  } else if (auth === 'bearer-env') {
    const token = env[provider.transport?.tokenEnv]; if (!token) throw new Error(`missing bearer token env for provider ${provider.id}`); headers.authorization = `Bearer ${token}`;
  } else if (auth === 'cloudflare-service-token-env') {
    const id = env[provider.transport?.clientIdEnv ?? 'CF_ACCESS_CLIENT_ID']; const secret = env[provider.transport?.clientSecretEnv ?? 'CF_ACCESS_CLIENT_SECRET'];
    if (!id || !secret) throw new Error(`missing Cloudflare service token env for provider ${provider.id}`);
    headers['CF-Access-Client-Id'] = id; headers['CF-Access-Client-Secret'] = secret;
  } else if (auth === 'gcp-metadata-oidc') {
    headers.authorization = `Bearer ${await gcpIdentityToken(provider.endpoint, provider.transport?.audience)}`;
  } else if (auth !== 'none') throw new Error(`unsupported transport auth: ${auth}`);
  return headers;
}
async function gcpIdentityToken(endpoint, audienceOverride) {
  const audience = audienceOverride ?? endpoint; if (!audience) throw new Error('GCP OIDC audience is required');
  const url = new URL('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity');
  url.searchParams.set('audience', audience); url.searchParams.set('format', 'full');
  const response = await fetch(url, { headers: { 'Metadata-Flavor': 'Google' }, signal: AbortSignal.timeout(2000) });
  if (!response.ok) throw new Error(`GCP metadata identity token failed: ${response.status}`); return response.text();
}
