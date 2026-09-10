import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';
import { randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import { getHeapStatistics } from 'node:v8';
import { createInitialLifeState, stableFingerprint, stepLife } from '../lib/life-core.mjs';
import { recoverUncommittedPartialJournalTail } from '../lib/life-journal-tail.mjs';
import { acquireLease, createLeaseOwnerId, refreshLease, releaseLease } from '../lib/life-lease.mjs';

const DEFAULT_PULSE_MS = 20_000;
const MIN_PULSE_MS = 5_000;
const MAX_PULSE_MS = 60 * 60_000;
const DEFAULT_LEASE_TTL_MS = 90_000;

export class LifeDaemon {
  constructor({
    statePath = process.env.DEUS_LIFE_STATE_PATH || './storage/deus-life-state.json',
    journalPath = process.env.DEUS_LIFE_JOURNAL_PATH || './storage/deus-life-events.ndjson',
    leasePath = process.env.DEUS_LIFE_LEASE_PATH || './storage/deus-life.lock',
    checkpointPath = process.env.DEUS_LIFE_CHECKPOINT_PATH || './storage/deus-life-checkpoint.json',
    pendingPath = process.env.DEUS_LIFE_PENDING_PATH || `${statePath}.pending`,
    pulseMs = Number(process.env.DEUS_LIFE_PULSE_MS || DEFAULT_PULSE_MS),
    leaseTtlMs = Number(process.env.DEUS_LIFE_LEASE_TTL_MS || DEFAULT_LEASE_TTL_MS),
    ownerId = createLeaseOwnerId(),
    sampleRuntime = defaultRuntimeSampler,
    faultInjector = async () => {},
    now = () => Date.now(),
    logger = console,
  } = {}) {
    this.statePath = statePath;
    this.backupPath = `${statePath}.bak`;
    this.journalPath = journalPath;
    this.leasePath = leasePath;
    this.checkpointPath = checkpointPath;
    this.pendingPath = pendingPath;
    this.pulseMs = boundedMs(pulseMs, MIN_PULSE_MS, MAX_PULSE_MS, 'DEUS_LIFE_PULSE_MS');
    this.leaseTtlMs = boundedMs(leaseTtlMs, 10_000, 24 * 60 * 60_000, 'DEUS_LIFE_LEASE_TTL_MS');
    if (this.leaseTtlMs <= this.pulseMs * 2) throw new Error('DEUS_LIFE_LEASE_TTL_MS must be greater than 2 × pulse interval');
    this.ownerId = ownerId;
    this.sampleRuntime = sampleRuntime;
    this.faultInjector = faultInjector;
    this.now = now;
    this.logger = logger;
    this.state = null;
    this.running = false;
    this.timer = null;
    this.queue = [];
    this.processing = false;
    this.lastElu = performance.eventLoopUtilization();
    this.lease = null;
  }

  async start() {
    if (this.running) return this;
    await this.#ensureStorage();
    this.lease = await acquireLease({ leasePath: this.leasePath, ownerId: this.ownerId, ttlMs: this.leaseTtlMs, now: this.now });
    try {
      await this.#recoverPendingCommit();
      this.state = await this.#loadState();
      await this.#verifyJournalHead(this.state);
      await this.#resumeActuationIfNeeded();
      this.#beginIncarnation();
      this.running = true;
      await this.emit({ type: 'boot', source: 'life-daemon', allowLearning: false, metrics: await this.#sample() });
      this.#scheduleNextPulse();
      return this;
    } catch (error) {
      this.running = false;
      await releaseLease({ leasePath: this.leasePath, ownerId: this.ownerId }).catch(() => {});
      this.lease = null;
      throw error;
    }
  }

  async stop({ reason = 'requested-stop' } = {}) {
    if (!this.running && !this.lease) return;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (this.running) {
      this.state.lastShutdownAt = new Date(this.now()).toISOString();
      await this.emit({ type: 'shutdown', source: 'life-daemon', allowLearning: false, payload: { reason } });
    }
    this.running = false;
    await this.#drain();
    await releaseLease({ leasePath: this.leasePath, ownerId: this.ownerId });
    this.lease = null;
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

  #beginIncarnation() {
    const now = new Date(this.now()).toISOString();
    this.state = {
      ...this.state,
      lineageId: this.state?.lineageId || randomUUID(),
      incarnationId: randomUUID(),
      bootCount: Number.isSafeInteger(this.state?.bootCount) ? this.state.bootCount + 1 : 1,
      currentBootAt: now,
      lastShutdownAt: this.state?.lastShutdownAt ?? null,
    };
  }

  #scheduleNextPulse() {
    if (!this.running) return;
    const quiet = this.state?.consecutiveQuiet ?? 0;
    const adaptive = Math.min(MAX_PULSE_MS, this.pulseMs * Math.max(1, Math.min(16, 1 + quiet / 8)));
    const leaseSafeDelay = Math.min(adaptive, Math.max(MIN_PULSE_MS, Math.floor(this.leaseTtlMs / 3)));
    this.timer = setTimeout(async () => {
      try {
        await this.emit({ type: 'quiet-pulse', source: 'life-daemon', allowLearning: false, metrics: await this.#sample() });
      } catch (error) {
        this.logger.error?.(`DEUS life pulse failed: ${error.message}`);
        if (error.code === 'LIFE_LEASE_LOST' || error.code === 'LIFE_JOURNAL_DIVERGED') this.running = false;
      } finally {
        this.#scheduleNextPulse();
      }
    }, leaseSafeDelay);
    // Keep this timer referenced: the process owns a live handle while its host keeps it running.
  }

  async #sample() {
    try {
      const runtime = await this.sampleRuntime();
      const current = performance.eventLoopUtilization(this.lastElu);
      this.lastElu = performance.eventLoopUtilization();
      const eventLoopLoad = clamp01(current.utilization || 0);
      const heap = getHeapStatistics();
      const heapUsed = process.memoryUsage().heapUsed;
      const heapHeadroom = heap.heap_size_limit > 0 ? clamp01(1 - heapUsed / heap.heap_size_limit) : 1;
      const computeHeadroom = Math.min(1 - eventLoopLoad, heapHeadroom);
      return {
        computeHeadroom,
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
        if (this.lease) this.lease = await refreshLease({ leasePath: this.leasePath, ownerId: this.ownerId, ttlMs: this.leaseTtlMs, now: this.now });
        const event = this.queue.shift();
        const previous = this.state ?? createInitialLifeState(this.now());
        const { state: candidateState, record } = stepLife(previous, event, this.now());
        this.state = await this.#commitGeneration({ previous, candidateState, record, event });
        await this.#executeAndRecordActuation(record.action);
        this.logger.info?.(`DEUS life lineage=${shortId(this.state.lineageId)} body=${shortId(this.state.incarnationId)} gen=${this.state.generation} event=${record.eventType} action=${record.action} V=${record.viability.toFixed(3)} mutation=${record.mutation}`);
      }
    } finally {
      this.processing = false;
    }
  }

  async #commitGeneration({ previous, candidateState, record, event }) {
    const journalBase = {
      ...record,
      inputAt: event.at,
      lineageId: candidateState.lineageId ?? previous.lineageId ?? null,
      incarnationId: candidateState.incarnationId ?? previous.incarnationId ?? null,
      prevHash: previous.journalHead ?? null,
    };
    const journalHash = stableFingerprint(journalBase);
    const journalEnvelope = { ...journalBase, journalHash };
    const committedState = { ...candidateState, journalHead: journalHash };
    const pending = { version: 1, state: committedState, journal: journalEnvelope };

    await atomicWriteJson(this.pendingPath, pending);
    await this.faultInjector('after-pending', { state: committedState, journal: journalEnvelope });
    await fs.appendFile(this.journalPath, `${JSON.stringify(journalEnvelope)}\n`, 'utf8');
    await this.faultInjector('after-journal', { state: committedState, journal: journalEnvelope });
    await this.#persistState(committedState);
    await this.faultInjector('after-state', { state: committedState, journal: journalEnvelope });
    await fs.rm(this.pendingPath, { force: true });
    return committedState;
  }

  async #recoverPendingCommit() {
    const pending = await readJsonOrNull(this.pendingPath);
    if (!pending?.state || !pending?.journal?.journalHash) return;

    const { journalHash, ...journalBase } = pending.journal;
    if (stableFingerprint(journalBase) !== journalHash) {
      const error = new Error('pending life journal hash verification failed');
      error.code = 'LIFE_JOURNAL_DIVERGED';
      throw error;
    }

    const currentState = await readValidState(this.statePath);
    if (currentState?.generation > pending.state.generation) {
      await fs.rm(this.pendingPath, { force: true });
      return;
    }

    let tail;
    try {
      tail = await readLastJsonLine(this.journalPath);
    } catch (error) {
      if (!(error instanceof SyntaxError)) throw error;
      const recovery = await recoverUncommittedPartialJournalTail({
        journalPath: this.journalPath,
        expectedCommittedHead: currentState?.journalHead ?? null,
      });
      tail = recovery.tail;
      this.logger.warn?.(`DEUS life trimmed ${recovery.truncatedBytes} uncommitted journal bytes before pending recovery`);
    }

    const observedHead = tail?.journalHash ?? null;
    const expectedPreviousHead = pending.journal.prevHash ?? null;

    if (observedHead !== journalHash) {
      if (observedHead !== expectedPreviousHead) {
        const error = new Error('pending generation does not extend the current life journal head');
        error.code = 'LIFE_JOURNAL_DIVERGED';
        error.observedHead = observedHead;
        error.expectedPreviousHead = expectedPreviousHead;
        throw error;
      }
      await fs.appendFile(this.journalPath, `${JSON.stringify(pending.journal)}\n`, 'utf8');
    }

    await this.#persistState(pending.state);
    await fs.rm(this.pendingPath, { force: true });
    this.logger.warn?.(`DEUS life recovered pending generation ${pending.state.generation}`);
  }

  async #verifyJournalHead(state) {
    if (!state?.journalHead) return;
    const tail = await readLastJsonLine(this.journalPath);
    if (!tail || tail.journalHash !== state.journalHead) {
      const error = new Error('life journal head does not match persisted state');
      error.code = 'LIFE_JOURNAL_DIVERGED';
      throw error;
    }
    const { journalHash, ...base } = tail;
    if (stableFingerprint(base) !== journalHash) {
      const error = new Error('life journal tail hash verification failed');
      error.code = 'LIFE_JOURNAL_DIVERGED';
      throw error;
    }
  }

  async #resumeActuationIfNeeded() {
    if (!this.state?.generation || !this.state?.lastAction) return;
    if (this.state.lastActuation?.generation === this.state.generation) return;
    await this.#executeAndRecordActuation(this.state.lastAction, { recovery: true });
  }

  async #executeAndRecordActuation(action, { recovery = false } = {}) {
    const result = await this.#actuate(action, this.state);
    this.state = {
      ...this.state,
      lastActuation: {
        generation: this.state.generation,
        action,
        recovery,
        ...result,
        at: new Date(this.now()).toISOString(),
      },
    };
    await this.#persistState(this.state);
  }

  async #actuate(action, state) {
    try {
      switch (action) {
        case 'VERIFY_REPAIR': {
          const primary = await readValidState(this.statePath);
          if (!primary || primary.generation !== state.generation) throw new Error('state readback mismatch');
          await this.#verifyJournalHead(state);
          return { status: 'ok', effect: 'state-and-journal-readback-verified' };
        }
        case 'CONSOLIDATE':
        case 'PRESERVE_CONTEXT':
        case 'COMPRESS_SERIALIZE':
          await this.#writeCheckpoint(state, action);
          return { status: 'ok', effect: 'checkpoint-written' };
        case 'INSPECT_TEST':
          return { status: 'ok', effect: 'runtime-observed' };
        case 'HOLD_STEADY':
        default:
          return { status: 'ok', effect: 'no-op' };
      }
    } catch (error) {
      this.logger.warn?.(`DEUS life actuator ${action} failed: ${error.message}`);
      return { status: 'error', effect: 'actuator-failed', errorClass: error?.name || 'Error' };
    }
  }

  async #writeCheckpoint(state, reason) {
    const checkpoint = {
      version: state.version,
      lineageId: state.lineageId,
      incarnationId: state.incarnationId,
      bootCount: state.bootCount,
      generation: state.generation,
      journalHead: state.journalHead,
      body: state.body,
      lastAction: state.lastAction,
      lastEventAt: state.lastEventAt,
      reason,
      writtenAt: new Date(this.now()).toISOString(),
    };
    await atomicWriteJson(this.checkpointPath, checkpoint);
  }

  async #ensureStorage() {
    for (const filePath of [this.statePath, this.journalPath, this.leasePath, this.checkpointPath, this.pendingPath]) {
      await fs.mkdir(path.dirname(filePath), { recursive: true });
    }
  }

  async #loadState() {
    const primary = await readValidState(this.statePath);
    if (primary) return primary;
    const backup = await readValidState(this.backupPath);
    if (backup) {
      this.logger.warn?.('DEUS life primary state invalid/missing; recovered from backup');
      return backup;
    }
    return createInitialLifeState(this.now());
  }

  async #persistState(state) {
    try { await fs.copyFile(this.statePath, this.backupPath); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    await atomicWriteJson(this.statePath, state);
  }
}

async function readValidState(filePath) {
  const parsed = await readJsonOrNull(filePath);
  if (!parsed || typeof parsed !== 'object' || !parsed.body || !Number.isSafeInteger(parsed.generation)) return null;
  return parsed;
}

async function readJsonOrNull(filePath) {
  try {
    return JSON.parse(await fs.readFile(filePath, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT' || error instanceof SyntaxError) return null;
    throw error;
  }
}

async function readLastJsonLine(filePath) {
  let handle;
  try {
    handle = await fs.open(filePath, 'r');
    const stat = await handle.stat();
    if (stat.size === 0) return null;
    let bytes = Math.min(stat.size, 64 * 1024);
    while (bytes <= stat.size) {
      const buffer = Buffer.alloc(bytes);
      await handle.read(buffer, 0, bytes, stat.size - bytes);
      const lines = buffer.toString('utf8').trim().split(/\r?\n/u).filter(Boolean);
      if (lines.length > 1 || bytes === stat.size) return JSON.parse(lines.at(-1));
      const next = Math.min(stat.size, bytes * 2);
      if (next === bytes) return JSON.parse(lines.at(-1));
      bytes = next;
    }
    return null;
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  } finally {
    await handle?.close().catch(() => {});
  }
}

async function atomicWriteJson(filePath, value) {
  const tmp = `${filePath}.${process.pid}.${randomUUID()}.tmp`;
  await fs.writeFile(tmp, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  await fs.rename(tmp, filePath);
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

  await new Promise(() => {});
}

function boundedMs(value, min, max, name) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(`${name} must be between ${min} and ${max} ms`);
  return n;
}

function clamp01(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function shortId(value) {
  return typeof value === 'string' ? value.slice(0, 8) : 'unknown';
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runLifeDaemon().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
