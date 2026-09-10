import { createWorkerServer } from './server.mjs';
import { createProviderHeartbeatClientFromEnv } from './heartbeat.mjs';
import { safeDefaultHandlers } from './handlers.mjs';
import { LifeDaemon } from './life-daemon.mjs';

export function publicLifeSnapshot(state) {
  if (!state || typeof state !== 'object') return null;
  return {
    version: state.version ?? null,
    generation: state.generation ?? null,
    body: state.body ? structuredClone(state.body) : null,
    lastAction: state.lastAction ?? null,
    lastEventAt: state.lastEventAt ?? null,
    lastMutationAt: state.lastMutationAt ?? null,
    consecutiveQuiet: state.consecutiveQuiet ?? 0,
    totalEvents: state.totalEvents ?? 0,
    totalMutations: state.totalMutations ?? 0,
    totalErrors: state.totalErrors ?? 0,
  };
}

export function wrapHandlersWithLifeEvents(handlers, daemon) {
  const source = handlers instanceof Map ? handlers : new Map(Object.entries(handlers));
  const wrapped = new Map();

  for (const [capability, handler] of source.entries()) {
    wrapped.set(capability, async (payload, context = {}) => {
      const taskId = context?.task?.id ?? null;
      const eventBase = { source: 'federation-worker', payload: { taskId, capability } };
      await safeEmit(daemon, { ...eventBase, type: 'task-start', allowLearning: false });
      try {
        const result = await handler(payload, context);
        await safeEmit(daemon, { ...eventBase, type: 'task-success', reward: 0.5 });
        return result;
      } catch (error) {
        await safeEmit(daemon, { ...eventBase, type: 'task-error', reward: -0.5, payload: { ...eventBase.payload, errorClass: error?.name ?? 'Error' } });
        throw error;
      }
    });
  }

  return wrapped;
}

export function installLifeCapabilities(handlers, daemon) {
  const target = handlers instanceof Map ? handlers : new Map(Object.entries(handlers));
  target.set('life.snapshot', async () => publicLifeSnapshot(daemon.snapshot()));
  return target;
}

export async function startLifeWorkerFromEnv({ logger = console } = {}) {
  let server = null;
  let heartbeat = null;
  let shuttingDown = false;

  const daemon = new LifeDaemon({
    logger,
    sampleRuntime: async () => {
      const federation = server?.getFederationState?.();
      if (!federation) return { humanAutonomy: 1, signalLoad: 0 };
      const load = Math.max(0, Math.min(1, federation.inFlight / Math.max(1, federation.maxConcurrency)));
      return {
        humanAutonomy: 1,
        signalLoad: load,
        progress: load > 0 ? 0.65 : 0.90,
        risk: 0.08 + load * 0.10,
      };
    },
  });

  await daemon.start();
  const handlers = installLifeCapabilities(wrapHandlersWithLifeEvents(safeDefaultHandlers, daemon), daemon);
  server = createWorkerServer({ handlers });

  const port = Number(process.env.PORT || 8790);
  const host = process.env.HOST || '127.0.0.1';

  server.listen(port, host, () => {
    logger.info?.(`BL federation life-worker listening on http://${host}:${port}`);
    try {
      heartbeat = createProviderHeartbeatClientFromEnv({
        getInFlight: () => server.getFederationState().inFlight,
        onError: (error) => {
          logger.warn?.(`provider heartbeat failed: ${error.message}`);
          void safeEmit(daemon, { type: 'external-novelty', source: 'provider-heartbeat', allowLearning: false, payload: { errorClass: error?.name ?? 'Error' }, metrics: { uncertainty: 0.45 } });
        },
      });
      if (heartbeat) {
        heartbeat.start();
        logger.info?.('BL federation life-worker heartbeat enabled');
      }
    } catch (error) {
      logger.error?.(`BL federation life-worker heartbeat configuration failed: ${error.message}`);
      void shutdown('heartbeat-config-error', 1);
    }
  });

  async function shutdown(reason = 'requested-stop', exitCode = 0) {
    if (shuttingDown) return;
    shuttingDown = true;
    heartbeat?.stop();
    await new Promise((resolve) => {
      if (!server.listening) return resolve();
      server.close(() => resolve());
    });
    await daemon.stop({ reason });
    if (exitCode !== null) process.exitCode = exitCode;
  }

  server.once('close', () => heartbeat?.stop());
  process.once('SIGINT', () => void shutdown('SIGINT', 0));
  process.once('SIGTERM', () => void shutdown('SIGTERM', 0));

  return { server, daemon, shutdown };
}

async function safeEmit(daemon, event) {
  try { await daemon.emit(event); }
  catch (error) { daemon.logger?.warn?.(`DEUS life event write failed: ${error.message}`); }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  startLifeWorkerFromEnv().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
