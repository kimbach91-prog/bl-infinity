import dns from 'node:dns/promises';
import net from 'node:net';

export async function validateWorkerEndpoint(endpoint, { allowInsecureLocalhost = true, allowPrivateNetwork = false, resolveDns = true } = {}) {
  if (!endpoint) throw new Error('provider endpoint is required');
  const url = new URL(endpoint);
  if (url.username || url.password) throw new Error('provider endpoint must not contain credentials');
  if (url.hash) throw new Error('provider endpoint must not contain fragment');
  const localName = ['localhost', '127.0.0.1', '::1'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(allowInsecureLocalhost && localName && url.protocol === 'http:')) throw new Error('remote worker endpoint must use https');
  if (!['https:', 'http:'].includes(url.protocol)) throw new Error('unsupported worker endpoint protocol');
  if (net.isIP(url.hostname)) {
    if (isRestrictedIp(url.hostname) && !(allowPrivateNetwork || localName)) throw new Error('worker endpoint IP is private/link-local/reserved');
    return url;
  }
  if (localName) return url;
  if (resolveDns) {
    const records = await dns.lookup(url.hostname, { all: true, verbatim: true });
    if (!records.length) throw new Error('worker endpoint DNS resolved to no addresses');
    if (records.some((r) => isRestrictedIp(r.address)) && !allowPrivateNetwork) throw new Error('worker endpoint resolves to private/link-local/reserved address');
  }
  return url;
}

export function isRestrictedIp(address) {
  const family = net.isIP(address);
  if (family === 4) {
    const p = address.split('.').map(Number); const [a,b] = p;
    return a === 0 || a === 10 || a === 127 || (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 192 && b === 0) || (a === 198 && (b === 18 || b === 19)) || a >= 224;
  }
  if (family === 6) {
    const s = address.toLowerCase();
    return s === '::' || s === '::1' || s.startsWith('fc') || s.startsWith('fd') || /^fe[89ab]/.test(s) || s.startsWith('ff') || s.startsWith('2001:db8:');
  }
  return false;
}
