import providers from "../config/providers.example.json" with { type: "json" };
import { ProviderRegistry, planRoute } from "../lib/fabric.mjs";

const registry = new ProviderRegistry(providers);

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "POST required" });
  try {
    const plan = planRoute(registry, req.body ?? {});
    return res.status(200).json(plan);
  } catch (error) {
    return res.status(400).json({ error: error.message });
  }
}
