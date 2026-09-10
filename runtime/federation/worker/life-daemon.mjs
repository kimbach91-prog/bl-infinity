import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';
import { performance } from 'node:perf_hooks';
import { createInitialLifeState, stepLife } from '../lib/life-core.mjs';

const DEFAULT_PULSE_MS = 20_000;
const MIN_PULSE_MS = 5_000;
const MAX_PULSE_MS = 60 * 60_000;

export class LifeDaemon {
  constructor({
    statePath = process.env.DEUS_LIFE_STATE_PATH || './storage/deus-life-state.json',
    journalPath = process.env.DEUS_LIFE_JOURNAL_PATH || './storage/deus-life-events.ndjson',
    pulseMs = Number(process.env.DEUS_LIFE_PULSE_MS || DEFAULT_PULSE_MS),
    sampleRuntime = defaultRuntimeSampler,
    now = () => Date.now(),
    logger = console,
  } = {}) {
    this.statePath = statePath;
    this.journalPath = journalPath;
    this.pulseMs = boundedMs(pulseMs, MIN_PULSE_MS, MAX_PULSE_MS, 'DEUS_LIFE_PULSE_MS');
    this.sampleRuntime = sampleRuntime;
    this.now = now;
    this.logger = logger;
    this.state = null;
    this.running = false;
    this.timer = null;
    this.queue = [];
    this.processing = false;
    this.lastElu = performance.eventLoopUtilization();
  }

  async start() {
    if (this.running) return this;
    await this.#ensureStorage();
    this.state = await this.#loadState();
    this.running = true;
    await this.emit({ type: 'boot', source: 'life-daemon', allowLearning: false, metrics: await this.#sample() });
    this.#scheduleNextPulse();
    return this;
  }

  async stop({ reason = 'requested-stop' } = {}) {
    if (!this.running) return;
    this.running = false;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    await this.emit({ type: 'shutdown', source: 'life-daemon', allowLearning: false, payload: { reason } });
    await this.#drain();
  }

  async emit(event) {
    if (!event || typeof event !== 'object') throw new Error('life event must be an object');
    this.queue.push({ ...event, at: new Date(this.now()).toISOString() });
    if (this.queue.length > 10_000) this.queue.splice(0, this.queue.length - 10_000);
    await this.#drain();
  }

  snapshot() {
    return this.state ? structuredClone(this.state) : null;
  }

  #scheduleNextPulse() {
    if (!this.running) return;
    const quiet = this.state?.consecutiveQuiet ?? 0;
    const adaptive = Math.min(MAX_PULSE_MS, this.pulseMs * Math.max(1, Math.min(16, 1 + quiet / 8)));
    this.timer = setTimeout(async () => {
      try {
        await this.emit({ type: 'quiet-pulse', source: 'life-daemon', allowLearning: false, metrics: await this.#sample() });
      } catch (error) {
        this.logger.error?.(`DEUS life pulse failed: ${error.message}`);
      } finally {
        this.#scheduleNextPulse();
      }
    }, adaptive);
    this.timer.unref?.();
  }

  async #sample() {
    try {
      const runtime = await this.sampleRuntime();
      const current = performance.eventLoopUtilization(this.lastElu);
      this.lastElu = performance.eventLoopUtilization();
      const elu = Math.max(0, Math.min(1, current.utilization || 0));
      return {
        computeHeadroom: 1 - elu,
        signalLoad: runtime?.signalLoad,
        progress: runtime?.progress,
        uncertainty: runtime?.uncertainty,
        risk: runtime?.risk,
        coherence: runtime?.coherence,
        memoryIntegrity: runtime?.memoryIntegrity,
        humanAutonomy: runtime?.humanAutonomy ?? 1,
        trustQuality: runtime?.trustQuality,
        contextContinuity: runtime?.contextContinuity,
      };
    } catch (error) {
      this.logger.warn?.(`DEUS life sampler failed: ${error.message}`);
      return { coherence: 0.75, uncertainty: 0.45 };
    }
  }

  async #drain() {
    if (this.processing) return;
    this.processing = true;
    try {
      while (this.queue.length) {
        const event = this.queue.shift();
        const { state, record } = stepLife(this.state ?? createInitialLifeState(this.now()), event, this.now());
        this.state = state;
        await this.#persistState(state);
        await fs.appendFile(this.journalPath, `${JSON.stringify({ ...record, inputAt: event.at })}\n`, 'utf8');
        this.logger.info?.(`DEUS life gen=${state.generation} event=${record.eventType} action=${record.action} V=${record.viability.toFixed(3)} mutation=${record.mutation}`);
      }
    } finally {
      this.processing = false;
    }
  }

  async #ensureStorage() {
    await fs.mkdir(path.dirname(this.statePath), { recursive: true });
    await fs.mkdir(path.dirname(this.journalPath), { recursive: true });
  }

  async #loadState() {
    try {
      const raw = await fs.readFile(this.statePath, 'utf8');
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || !parsed.body) throw new Error('invalid state');
      return parsed;
    } catch (error) {
      if (error.code !== 'ENOENT') this.logger.warn?.(`DEUS life state reset: ${error.message}`);
      return createInitialLifeState(this.now());
    }
  }

  async #persistState(state) {
    const tmp = `${this.statePath}.${process.pid}.tmp`;
    await fs.writeFile(tmp, `${JSON.stringify(state, null, 2)}\n`, 'utf8');
    await fs.rename(tmp, this.statePath);
  }
}

export async function defaultRuntimeSampler() {
  return { humanAutonomy: 1 };
}

export function attachStdinEventBridge(daemon, { input = process.stdin } = {}) {
  if (!input || input.destroyed) return null;
  const rl = readline.createInterface({ input, crlfDelay: Infinity });
  rl.on('line', async (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    try {
      const parsed = JSON.parse(trimmed);
      await daemon.emit(parsed);
    } catch {
      await daemon.emit({ type: 'external-novelty', source: 'stdin', payload: { text: trimmed } });
    }
  });
  return rl;
}

export async function runLifeDaemon(options = {}) {
  const daemon = new LifeDaemon(options);
  await daemon.start();
  const rl = process.stdin.isTTY ? null : attachStdinEventBridge(daemon);

  const shutdown = async (signal) => {
    try { rl?.close(); } catch {}
    try { await daemon.stop({ reason: signal }); }
    finally { process.exit(0); }
  };
  process.once('SIGINT', () => void shutdown('SIGINT'));
  process.once('SIGTERM', () => void shutdown('SIGTERM'));

  // A real daemon remains alive while the host keeps this process alive.
  // Its work is event-driven; quiet periods back off instead of inventing mutations.
  await new Promise(() => {});
}

function boundedMs(value, min, max, name) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(`${name} must be between ${min} and ${max} ms`);
  return n;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runLifeDaemon().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
