import { ProviderRegistry, planRoute } from '../lib/fabric.mjs';

function providersFromEnv() {
  const raw = process.env.BL_PROVIDERS_JSON;
  if (!raw) return [];
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) throw new Error('BL_PROVIDERS_JSON must be an array');
  return parsed;
}

export default async function handler(req, res) {
  res.setHeader('cache-control', 'no-store');
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });
  try {
    const registry = new ProviderRegistry(providersFromEnv());
    return res.status(200).json(planRoute(registry, req.body ?? {}));
  } catch (error) {
    return res.status(400).json({ error: error.message });
  }
}
