import { ProviderRegistry } from './fabric.mjs';
import { FederationExecutor } from './executor.mjs';
import { TelemetryBook } from './telemetry.mjs';
import { MemoryAuditLog } from './audit.mjs';
import { LocalAdapter } from '../adapters/local.mjs';
import { HttpWorkerAdapter } from '../adapters/http-worker.mjs';

export function createFederationRuntime({ providers = [], localHandlers = {}, manifestVerifier = null, audit = new MemoryAuditLog() } = {}) {
  const telemetry = new TelemetryBook();
  const seeded = providers.map((provider) => { telemetry.ensure(provider.id, provider.telemetry ?? {}); return { ...structuredClone(provider), telemetry: telemetry.snapshot(provider.id) }; });
  const registry = new ProviderRegistry(seeded, { manifestVerifier });
  const executor = new FederationExecutor({ registry, telemetry, audit, adapters: { local: new LocalAdapter(localHandlers), 'http-worker': new HttpWorkerAdapter(), 'cloudflare-worker': new HttpWorkerAdapter(), 'gcp-cloud-run': new HttpWorkerAdapter(), 'vercel-function': new HttpWorkerAdapter() } });
  return { registry, telemetry, executor, audit };
}
