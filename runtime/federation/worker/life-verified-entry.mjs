import { attachStdinEventBridge, LifeDaemon } from './life-daemon.mjs';
import { verifyPersistentLifeStateIfPresent, verifyRunningLifeSnapshot } from '../lib/life-deep-gate.mjs';

export async function runVerifiedLifeDaemon(options = {}) {
  const statePath = options.statePath || process.env.DEUS_LIFE_STATE_PATH || './storage/deus-life-state.json';
  const journalPath = options.journalPath || process.env.DEUS_LIFE_JOURNAL_PATH || './storage/deus-life-events.ndjson';
  const pendingPath = options.pendingPath || process.env.DEUS_LIFE_PENDING_PATH || `${statePath}.pending`;

  await verifyPersistentLifeStateIfPresent({ statePath, journalPath, pendingPath });

  const daemon = new LifeDaemon({ ...options, statePath, journalPath, pendingPath });
  await daemon.start();
  try {
    await verifyRunningLifeSnapshot({ snapshot: daemon.snapshot(), journalPath });
  } catch (error) {
    await daemon.stop({ reason: 'deep-integrity-gate-failed' }).catch(() => {});
    throw error;
  }

  const rl = process.stdin.isTTY ? null : attachStdinEventBridge(daemon);
  let shuttingDown = false;
  const shutdown = async (signal) => {
    if (shuttingDown) return;
    shuttingDown = true;
    try { rl?.close(); } catch {}
    try { await daemon.stop({ reason: signal }); }
    finally { process.exit(0); }
  };
  process.once('SIGINT', () => void shutdown('SIGINT'));
  process.once('SIGTERM', () => void shutdown('SIGTERM'));

  await new Promise(() => {});
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runVerifiedLifeDaemon().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
