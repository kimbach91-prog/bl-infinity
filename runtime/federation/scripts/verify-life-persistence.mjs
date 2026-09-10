import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { stableFingerprint } from '../lib/life-core.mjs';

const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-persistence-'));
const statePath = path.join(dir, 'state.json');
const journalPath = path.join(dir, 'journal.ndjson');
const leasePath = path.join(dir, 'life.lock');
const checkpointPath = path.join(dir, 'checkpoint.json');

try {
  const first = startDaemon();
  await waitForGeneration(2, 15_000);
  await stopDaemon(first);
  const state1 = await readState();
  const journal1 = await readJournal();
  verifyChain(journal1, state1);
  assert(state1.generation >= 3, `first run expected >=3 generations, got ${state1.generation}`);
  assert(typeof state1.lineageId === 'string', 'first run must create a stable lineage id');
  assert(typeof state1.incarnationId === 'string', 'first run must create an incarnation id');
  assert(state1.bootCount === 1, `first run expected bootCount=1, got ${state1.bootCount}`);
  assert(journal1.length >= state1.generation, 'first run journal must contain every persisted generation');
  await assertLeaseReleased();

  const second = startDaemon();
  await waitForGeneration(state1.generation + 2, 15_000);
  await stopDaemon(second);
  const state2 = await readState();
  const journal2 = await readJournal();
  verifyChain(journal2, state2);
  assert(state2.generation > state1.generation, 'restart must resume and advance prior lineage');
  assert(state2.lineageId === state1.lineageId, 'lineage id must survive restart');
  assert(state2.incarnationId !== state1.incarnationId, 'new process body must receive a new incarnation id');
  assert(state2.bootCount === state1.bootCount + 1, 'boot count must increment exactly once per new process incarnation');
  assert(state2.totalEvents > state1.totalEvents, 'event counter must survive restart and continue');
  assert(typeof state2.lastShutdownAt === 'string', 'graceful stop must persist shutdown time');
  assert(journal2.length >= state2.generation, 'journal must remain append-only across restart');
  assert(journal2.length > journal1.length, 'journal must grow after restart');
  assert(journal2.filter((row) => row.eventType === 'quiet-pulse').every((row) => row.action === 'HOLD_STEADY'), 'healthy quiet pulses must hold steady');
  assert(journal2.every((row) => row.lineageId === state1.lineageId), 'all journal generations must retain the same lineage id');
  await assertLeaseReleased();

  console.log(JSON.stringify({
    ok: true,
    lineageId: state2.lineageId,
    firstIncarnationId: state1.incarnationId,
    secondIncarnationId: state2.incarnationId,
    bootCount: state2.bootCount,
    firstGeneration: state1.generation,
    finalGeneration: state2.generation,
    firstJournalLines: journal1.length,
    finalJournalLines: journal2.length,
    journalHead: state2.journalHead,
    hashChainVerified: true,
    resumed: state2.generation > state1.generation,
    lineagePreserved: state2.lineageId === state1.lineageId,
    incarnationReplaced: state2.incarnationId !== state1.incarnationId,
    quietHoldSteady: true,
    leaseReleased: true,
  }));
} finally {
  await fs.rm(dir, { recursive: true, force: true });
}

function startDaemon() {
  const child = spawn(process.execPath, ['worker/life-daemon.mjs'], {
    cwd: new URL('..', import.meta.url),
    env: {
      ...process.env,
      DEUS_LIFE_STATE_PATH: statePath,
      DEUS_LIFE_JOURNAL_PATH: journalPath,
      DEUS_LIFE_LEASE_PATH: leasePath,
      DEUS_LIFE_CHECKPOINT_PATH: checkpointPath,
      DEUS_LIFE_PULSE_MS: '5000',
      DEUS_LIFE_LEASE_TTL_MS: '20000',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => { stdout += chunk; });
  child.stderr.on('data', (chunk) => { stderr += chunk; });
  child.captured = () => ({ stdout, stderr });
  return child;
}

async function stopDaemon(child) {
  if (child.exitCode !== null) {
    const logs = child.captured();
    throw new Error(`life daemon exited early code=${child.exitCode}\n${logs.stderr}\n${logs.stdout}`);
  }
  child.kill('SIGTERM');
  const { code, signal } = await waitForExit(child, 10_000);
  if (code !== 0) {
    const logs = child.captured();
    throw new Error(`life daemon did not stop cleanly code=${code} signal=${signal}\n${logs.stderr}\n${logs.stdout}`);
  }
}

async function waitForGeneration(minGeneration, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const state = await readState();
      if (state.generation >= minGeneration) return state;
    } catch {}
    await sleep(150);
  }
  throw new Error(`timed out waiting for generation >= ${minGeneration}`);
}

async function readState() {
  return JSON.parse(await fs.readFile(statePath, 'utf8'));
}

async function readJournal() {
  const raw = await fs.readFile(journalPath, 'utf8');
  return raw.split(/\r?\n/u).filter(Boolean).map((line) => JSON.parse(line));
}

function verifyChain(rows, state) {
  let previousHash = null;
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    const { journalHash, ...base } = row;
    assert(typeof journalHash === 'string', `missing journal hash at line ${index + 1}`);
    assert(stableFingerprint(base) === journalHash, `journal hash mismatch at line ${index + 1}`);
    assert((row.prevHash ?? null) === previousHash, `journal prevHash mismatch at line ${index + 1}`);
    previousHash = journalHash;
  }
  assert(state.journalHead === previousHash, 'state journalHead must equal verified journal tail');
}

async function assertLeaseReleased() {
  try {
    await fs.access(leasePath);
    throw new Error('life lease still exists after graceful shutdown');
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
}

function waitForExit(child, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error('timed out waiting for daemon exit'));
    }, timeoutMs);
    child.once('exit', (code, signal) => {
      clearTimeout(timer);
      resolve({ code, signal });
    });
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
