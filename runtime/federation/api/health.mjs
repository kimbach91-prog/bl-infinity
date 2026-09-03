export default async function handler(_req, res) {
  res.setHeader('cache-control', 'no-store');
  res.status(200).json({ ok: true, service: 'bl-compute-federation', version: '0.2.0' });
}
