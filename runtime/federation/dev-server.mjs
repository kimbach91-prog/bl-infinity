import http from "node:http";
import providers from "./config/providers.example.json" with { type: "json" };
import { ProviderRegistry, planRoute } from "./lib/fabric.mjs";

const registry = new ProviderRegistry(providers);
const port = Number(process.env.PORT || 8787);

const server = http.createServer(async (req, res) => {
  res.setHeader("content-type", "application/json; charset=utf-8");
  if (req.url === "/health") return res.end(JSON.stringify({ ok: true, service: "bl-compute-federation" }));
  if (req.url === "/route" && req.method === "POST") {
    let raw = "";
    for await (const chunk of req) raw += chunk;
    try {
      const plan = planRoute(registry, JSON.parse(raw || "{}"));
      res.statusCode = 200;
      return res.end(JSON.stringify(plan, null, 2));
    } catch (e) {
      res.statusCode = 400;
      return res.end(JSON.stringify({ error: e.message }));
    }
  }
  res.statusCode = 404;
  res.end(JSON.stringify({ error: "not found" }));
});
server.listen(port, () => console.log(`BL federation control plane listening on :${port}`));
