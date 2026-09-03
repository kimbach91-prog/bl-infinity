import { ProviderRegistry } from './fabric.mjs';
import { FederationExecutor } from './executor.mjs';
import { TelemetryBook } from './telemetry.mjs';
import { CircuitBreakerBook } from './circuit.mjs';
import { MemoryAuditLog } from './audit.mjs';
import { LocalAdapter } from '../adapters/local.mjs';
import { HttpWorkerAdapter } from '../adapters/http-worker.mjs';
import { FederationOrchestrator } from './orchestrator.mjs';
import { BudgetGovernor } from './budget.mjs';

export function createFederationRuntime({ providers = [], localHandlers = {}, manifestVerifier = null, audit = null, budgetConfig = {}, state = null } = {}) {
  const effectiveAudit = audit ?? state?.audit ?? new MemoryAuditLog();
  const telemetry = new TelemetryBook(); const circuit = new CircuitBreakerBook();
  const seeded = providers.map((provider) => { telemetry.ensure(provider.id, provider.telemetry ?? {}); return { ...structuredClone(provider), telemetry: telemetry.snapshot(provider.id) }; });
  const registry = new ProviderRegistry(seeded, { manifestVerifier });
  const executor = new FederationExecutor({ registry, telemetry, circuit, audit: effectiveAudit, adapters: { local: new LocalAdapter(localHandlers), 'http-worker': new HttpWorkerAdapter(), 'cloudflare-worker': new HttpWorkerAdapter(), 'gcp-cloud-run': new HttpWorkerAdapter(), 'vercel-function': new HttpWorkerAdapter() } });
  const orchestrator = new FederationOrchestrator({ registry, executor, audit: effectiveAudit, queue: state?.queue, cache: state?.cache, ledger: state?.ledger, budget: state?.budget ?? new BudgetGovernor(budgetConfig) });
  return { registry, telemetry, circuit, executor, orchestrator, audit: effectiveAudit, state };
}
