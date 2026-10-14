// Candidate orchestration only. Runs the existing pinned integerSum operator.
// No provider API, private source, production grant, daemon, or model is admitted.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import * as fs from 'node:fs';
import path from 'node:path';
import { hostname, tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const BASE_COMMIT = 'ac72a9716e0100635ee0a66a586b517a9c7953f4';
const SOURCE_DIGEST = '277b3e36fe3aa4a9b5d39183bc41947653a25d964d47c84ad346347f7fd1fb1a';
const WORKER_DIGEST = '08f5a607474e70f8b808e074f67968db5f0683de5dc3c583191d20c870f4138e';
const ROOT_DIGEST = '3f1ead31adede86fcbf3e67b26a1d75c7ed4bd4955b1f12f2297bddb93a58dee';
const EXPECTED = Object.freeze({ sum: '460194' });
const CONTEXT = Object.freeze({ tenantId: 'deus', dataClass: 'public', sideEffect: false });
const ROUTE = 'github-ci-public-cpu';
const POOL = 'single-ci-runner';
const GRANT_MS = 15 * 60_000;
const LEASE_MS = 20_000;
const MAX_CARRIER_BYTES = 250_000;
const CARRIER = ['atoms.sqlite', 'federation.sqlite', 'graph.json', 'manifest.json', 'producer-receipt.json'];
const CONTENT_FILES = CARRIER.filter(x => x !== 'manifest.json');
const REPO = fs.realpathSync(fileURLToPath(new URL('../../../', import.meta.url)));
const LIB = path.join(REPO, 'runtime/federation/lib');
const WORKER = path.join(REPO, 'runtime/federation/worker/instruction-operators.mjs');
const SELF = fileURLToPath(import.meta.url);
const phase = process.argv[2];
const hash = x => createHash('sha256').update(x).digest('hex');
let api;

function need(ok, code) {
  if (!ok) throw Object.assign(new Error(code), { code });
}
function same(a, b, code) {
  assert.deepEqual(a, b, code);
}
function jsonFile(p) {
  const b = fs.readFileSync(p);
  need(b.length <= 64 * 1024, 'JSON_FILE_BOUND');
  return JSON.parse(b);
}
function writeJson(p, value) {
  fs.writeFileSync(p, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
}
function regular(p) {
  const s = fs.lstatSync(p);
  need(s.isFile() && !s.isSymbolicLink() && s.nlink === 1, 'REGULAR_SINGLE_LINK_FILE_REQUIRED');
  return s;
}
function pin(p, name = path.basename(p)) {
  const s = regular(p);
  need(s.size < MAX_CARRIER_BYTES, 'FILE_SIZE_BOUND');
  return { name, bytes: s.size, sha256: hash(fs.readFileSync(p)) };
}
function currentSourceSnapshot() {
  return fs.readdirSync(LIB, { withFileTypes: true })
    .filter(x => x.isFile() && x.name.endsWith('.mjs'))
    .map(x => {
      const p = path.join(LIB, x.name);
      const s = regular(p);
      return { name: x.name, bytes: s.size, sha: hash(fs.readFileSync(p)) };
    }).sort((a, b) => a.name.localeCompare(b.name));
}
// Exact flat source-snapshot schema from the pinned fixture. Canonical key order.
function sourceDigest(snapshot) {
  return hash(JSON.stringify(snapshot.map(x => ({ bytes: x.bytes, name: x.name, sha: x.sha }))));
}
function actualBytes(snapshot) {
  let sum = 0n;
  for (const entry of snapshot) {
    const raw = fs.readFileSync(path.join(LIB, entry.name));
    need(hash(raw) === entry.sha, 'SOURCE_CHANGED_AFTER_FREEZE');
    sum += BigInt(raw.length);
  }
  return sum.toString();
}
function runner() {
  need(process.env.GITHUB_ACTIONS === 'true', 'HOSTED_GITHUB_CI_REQUIRED');
  need(process.env.GITHUB_REPOSITORY === 'kimbach91-prog/bl-infinity', 'OWNER_REPOSITORY_REQUIRED');
  const sourceHead = process.env.DEUS_HANDOFF_SOURCE_SHA;
  need(/^[a-f0-9]{40}$/.test(sourceHead ?? ''), 'SOURCE_HEAD_PIN_REQUIRED');
  const actualHead = execFileSync('git', ['rev-parse', 'HEAD'], {
    cwd: REPO, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
  need(sourceHead === actualHead, 'ACTUAL_HEAD_MISMATCH');
  need(process.platform === 'linux' && process.versions.node.split('.')[0] === '22', 'PINNED_CI_ENVIRONMENT_REQUIRED');
  const kernelBootId = fs.readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim().toLowerCase();
  need(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(kernelBootId), 'LINUX_KERNEL_BOOT_ID_REQUIRED');
  const r = {
    hostname: hostname(), kernelBootId, job: process.env.GITHUB_JOB,
    runnerName: process.env.RUNNER_NAME ?? null, runnerOS: process.env.RUNNER_OS,
    workflowRunId: process.env.GITHUB_RUN_ID, workflowAttempt: process.env.GITHUB_RUN_ATTEMPT,
    sourceHead,
  };
  for (const k of ['hostname', 'job', 'runnerOS', 'workflowRunId', 'workflowAttempt'])
    need(typeof r[k] === 'string' && r[k].length > 0, 'RUNNER_IDENTITY_REQUIRED');
  need(process.platform === 'linux' && process.versions.node.split('.')[0] === '22', 'PINNED_CI_ENVIRONMENT_REQUIRED');
  return r;
}
function handoffDir() {
  const p = process.env.DEUS_HANDOFF_DIR;
  need(typeof p === 'string' && path.isAbsolute(p), 'ABSOLUTE_HANDOFF_DIRECTORY_REQUIRED');
  const resolved = path.resolve(p);
  need(resolved !== path.parse(resolved).root && resolved !== REPO, 'OWNED_HANDOFF_DIRECTORY_REQUIRED');
  if (fs.existsSync(resolved)) {
    const s = fs.lstatSync(resolved);
    need(s.isDirectory() && !s.isSymbolicLink(), 'HANDOFF_DIRECTORY_NOT_REGULAR');
    need(fs.realpathSync(resolved) === resolved, 'HANDOFF_DIRECTORY_LINK_ESCAPE');
  }
  return resolved;
}
function environment() {
  return { node: process.version, v8: process.versions.v8, sqlite: process.versions.sqlite,
    platform: process.platform, arch: process.arch, scope: 'github-actions-ci-public' };
}
async function loadApis() {
  const snap = currentSourceSnapshot();
  need(snap.length === 52 && sourceDigest(snap) === SOURCE_DIGEST, 'PINNED_52_MODULE_SOURCE_REQUIRED');
  need(actualBytes(snap) === EXPECTED.sum, 'SOURCE_BYTE_ORACLE_MISMATCH');
  need(hash(fs.readFileSync(WORKER)) === WORKER_DIGEST, 'PINNED_OPERATOR_REQUIRED');
  // No repo module is imported until its complete public lib footprint is pinned.
  const [fabric, runtime, sqlite, canonical, broker] = await Promise.all([
    import(pathToFileURL(path.join(LIB, 'instruction-fabric.mjs')).href),
    import(pathToFileURL(path.join(LIB, 'runtime.mjs')).href),
    import(pathToFileURL(path.join(LIB, 'sqlite-state.mjs')).href),
    import(pathToFileURL(path.join(LIB, 'canonical.mjs')).href),
    import(pathToFileURL(path.join(LIB, 'task-graph-broker.mjs')).href),
  ]);
  api = { ...fabric, ...runtime, ...sqlite, ...canonical, ...broker };
  need(api.sha256Json(snap) === SOURCE_DIGEST, 'SOURCE_CANONICAL_ENCODING_MISMATCH');
  need(api.sha256Json(EXPECTED) === ROOT_DIGEST, 'ROOT_ORACLE_DIGEST_MISMATCH');
  return snap;
}
function fixture(snapshot, runId) {
  const cut = Math.ceil(snapshot.length / 2), parts = [snapshot.slice(0, cut), snapshot.slice(cut)];
  const leafInputs = parts.map(s => ({ value: { numbers: s.map(x => String(x.bytes)) },
    upstream: {}, sourceDigest: api.sha256Json(s) }));
  const leafResults = parts.map(s => ({ sum: actualBytes(s) }));
  const canary = { value: { numbers: ['2', '3'] }, upstream: {}, sourceDigest: api.sha256Json('test-canary') };
  const reducerInput = { value: null, sourceDigest: null,
    upstream: { 'leaf-0': leafResults[0], 'leaf-1': leafResults[1] } };
  const frozen = [canary, ...leafInputs, reducerInput];
  const profiles = new Map(frozen.map((input, i) => [api.sha256Json(input),
    i === 0 ? { sum: '5' } : i < 3 ? leafResults[i - 1] : EXPECTED]));
  const verifyInput = input => profiles.has(api.sha256Json(input)) &&
    sourceDigest(currentSourceSnapshot()) === SOURCE_DIGEST;
  const verify = (output, input) => verifyInput(input) &&
    api.sha256Json(output) === api.sha256Json(profiles.get(api.sha256Json(input))) &&
    actualBytes(snapshot) === EXPECTED.sum;
  const op = {
    id: 'sum', programDigest: WORKER_DIGEST,
    verificationDigest: api.sha256Json({ contract: 'independent-file-stat-oracle-handoff/1',
      source: SOURCE_DIGEST, verifier: hash(verify.toString()), inputProfiles: [...profiles.keys()] }),
    environmentDigest: api.sha256Json({ node: process.version, scope: 'github-actions-ci-public' }),
    inputValidationDigest: api.sha256Json({ contract: 'source-footprint-handoff-input/1',
      source: SOURCE_DIGEST, validator: hash(verifyInput.toString()), inputProfiles: [...profiles.keys()] }),
    validateInput: verifyInput, verify, canary: { input: canary, expected: { sum: '5' } }, cacheTtlMs: 60000,
  };
  const graph = api.compileAtomTree({
    graphId: 'public-federation-module-footprint-handoff-r1', runId,
    leaves: leafInputs.map(x => ({ value: x.value, sourceDigest: x.sourceDigest })),
    leafOperator: 'sum', reducerOperator: 'sum', fanIn: 2, maxNodes: 3,
  });
  return { op, graph, leafResults };
}
function opRecord(op) {
  return { id: op.id, programDigest: op.programDigest, verificationDigest: op.verificationDigest,
    environmentDigest: op.environmentDigest, inputValidationDigest: op.inputValidationDigest };
}
function openContext(dir, snapshot, runId, authority, programOverride = null, withRuntime = true) {
  const f = fixture(snapshot, runId);
  if (programOverride) f.op.programDigest = programOverride;
  let state, store;
  try {
    store = new api.AtomStore(path.join(dir, 'atoms.sqlite'));
    state = api.createSqliteFederationState(path.join(dir, 'federation.sqlite'));
    const driver = new api.PinnedWorkerDriver({
      moduleUrl: pathToFileURL(WORKER).href, moduleDigest: WORKER_DIGEST,
      exportName: 'integerSum', heapMiB: 64, dependencyPins: [], allowedBuiltins: ['node:crypto'],
    });
    const binding = { routeId: ROUTE, poolId: POOL, slots: 1, maxLeaseMs: LEASE_MS,
      operatorIds: ['sum'], authority, driver };
    const fabric = new api.InstructionFabric({ store, bindings: [binding], operators: [f.op], reserveBytes: 0 });
    let runtime = null;
    if (withRuntime) {
      runtime = api.createFederationRuntime({
        providers: [fabric.provider(ROUTE)], state, allowedStateDataClasses: ['public'],
      });
      runtime.executor.adapters.set('instruction-atom', fabric.adapter());
    }
    return { ...f, state, store, fabric, runtime, driver, binding,
      bindingDigest: fabric.bindings.get(ROUTE).bindingHash };
  } catch (e) { state?.close(); store?.close(); throw e; }
}
function close(c) { try { c.state.close(); } finally { c.store.close(); } }
function counts(c) {
  return {
    active: Number(c.store.snapshot().active),
    unconfirmedStops: Number(c.store.db.prepare('SELECT COUNT(*) n FROM atom_leases WHERE stop_observed=0').get().n),
    runningJobs: c.state.queue.list({ state: 'running' }).length,
    leases: Number(c.store.db.prepare('SELECT COUNT(*) n FROM atom_leases').get().n),
    events: Number(c.store.db.prepare('SELECT COUNT(*) n FROM atom_events').get().n),
    graphReceipts: Number(c.store.db.prepare('SELECT COUNT(*) n FROM atom_task_receipts').get().n),
  };
}
function quiet(c) {
  const n = counts(c);
  need(n.active === 0 && n.unconfirmedStops === 0 && n.runningJobs === 0, 'OBSERVED_STOP_AND_NO_ACTIVE_LEASES_REQUIRED');
  c.store.verifyEvents();
  return n;
}
function firstRecord(c, id) {
  const job = c.state.queue.get(id);
  need(job?.state === 'succeeded' && job.attempts === 1, 'FIRST_JOB_NOT_SINGLE_SUCCESS');
  c.fabric.verifyPersistedTask(job);
  const row = c.store.db.prepare('SELECT task_hash,output_hash,receipt_json FROM atom_task_receipts WHERE task_id=?').get(id);
  const receipt = JSON.parse(row.receipt_json);
  need(receipt.kind === 'EXECUTED' && receipt.verdict === 'VERIFIED_FOR_OPERATOR_CONTRACT' &&
    receipt.stop?.exitCode === 0 && receipt.leaseId && Number.isSafeInteger(receipt.fence), 'FIRST_EXECUTED_STOP_RECEIPT_REQUIRED');
  return { taskId: id, attempts: job.attempts, taskHash: row.task_hash, outputHash: row.output_hash,
    receiptSha256: hash(row.receipt_json), leaseId: receipt.leaseId, fence: receipt.fence,
    kind: receipt.kind, verdict: receipt.verdict, stop: receipt.stop,
    leaseKey: receipt.key,
    leaseCount: Number(c.store.db.prepare('SELECT COUNT(*) n FROM atom_leases WHERE job_key=?').get(receipt.key).n) };
}
function noSidecars(dir) {
  for (const name of ['atoms.sqlite', 'federation.sqlite'])
    for (const suffix of ['-wal', '-shm']) need(!fs.existsSync(path.join(dir, name + suffix)), 'SQLITE_CLOSE_NOT_TRANSPORT_READY');
}
function makeDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  need(fs.realpathSync(dir) === dir && fs.readdirSync(dir).length === 0, 'EMPTY_OWNED_DIRECTORY_REQUIRED');
}
function cloneState(carrier) {
  const dir = fs.mkdtempSync(path.join(tmpdir(), 'deus-public-handoff-owned-'));
  for (const name of ['atoms.sqlite', 'federation.sqlite'])
    fs.copyFileSync(path.join(carrier, name), path.join(dir, name), fs.constants.COPYFILE_EXCL);
  return dir;
}
function removeOwned(dir) {
  need(path.dirname(dir) === fs.realpathSync(tmpdir()) &&
    path.basename(dir).startsWith('deus-public-handoff-owned-'), 'OWNED_SCRATCH_CONFINEMENT');
  fs.rmSync(dir, { recursive: true, force: true });
}
function authorityCurrent(a, issuedAt) {
  same(Object.keys(a).sort(), ['allowedDataClasses', 'consentRef', 'expiresAt', 'tenantId', 'zeroSpend'], 'CLOSED_PUBLIC_AUTHORITY');
  need(a.consentRef === 'GITHUB_CI_PUBLIC_TASK_ONLY' && a.tenantId === 'deus' &&
    a.zeroSpend === true, 'EXPLICIT_PUBLIC_ZERO_SPEND_AUTHORITY');
  same(a.allowedDataClasses, ['public'], 'PUBLIC_DATA_CEILING');
  need(Date.parse(a.expiresAt) === Date.parse(issuedAt) + GRANT_MS && Date.now() < Date.parse(a.expiresAt),
    'ORIGINAL_15_MINUTE_AUTHORITY_EXPIRED_OR_CHANGED');
}
async function rejectedWithoutMutation(c, label, fn, expected) {
  const before = quiet(c);
  let code = null;
  try { await fn(); } catch (e) { code = String(e.code ?? e.message); }
  need(code && expected.test(code), 'EXPECTED_REJECTION_MISSING:' + label);
  const after = quiet(c);
  same(after, before, 'REJECT_MUTATED_LEASES_OR_EVENTS:' + label);
  return { label, code, before, after, noNewLeasesOrEvents: true };
}
async function negatives(dir, snapshot, m) {
  const results = [];
  for (const kind of ['expired-grant', 'stale-program-contract', 'altered-graph']) {
    const owned = cloneState(dir); let c;
    try {
      const a = structuredClone(m.authority);
      if (kind === 'expired-grant') a.expiresAt = new Date(Date.parse(m.issuedAt) - 1).toISOString();
      const stale = kind === 'stale-program-contract' ?
        (WORKER_DIGEST[0] === '0' ? '1' : '0') + WORKER_DIGEST.slice(1) : null;
      c = openContext(owned, snapshot, m.runId, a, stale, kind === 'altered-graph');
      same(quiet(c), m.producerCounts, 'COPY_INITIAL_COUNTERS_CHANGED');
      if (kind === 'expired-grant')
        results.push(await rejectedWithoutMutation(c, kind,
          () => c.fabric.authorize(ROUTE, 'sum', CONTEXT), /AUTHORITY_EXPIRED_OR_REVOKED/));
      if (kind === 'stale-program-contract')
        results.push(await rejectedWithoutMutation(c, kind,
          () => c.fabric.verifyPersistedTask(c.state.queue.get(m.firstTask.taskId)), /PERSISTED_CONTRACT_CHANGED/));
      if (kind === 'altered-graph') {
        const altered = structuredClone(c.graph); altered.metadata.handoffTamper = true;
        const broker = new api.TaskGraphBroker(altered);
        results.push(await rejectedWithoutMutation(c, kind,
          () => broker.restoreFromQueue(c.runtime.orchestrator, { sweepExpired: false }),
          /FLOW_GRAPH_FINGERPRINT_MISMATCH/));
      }
    } finally { if (c) close(c); removeOwned(owned); }
  }
  return { schema: 'deus.public-handoff-negative-receipts/1', results, dispatched: false };
}
async function produce(dir, who, snapshot) {
  makeDir(dir);
  const issuedAt = new Date().toISOString(), runId = 'public-handoff-' + who.workflowRunId + '-' + who.workflowAttempt;
  const authority = { consentRef: 'GITHUB_CI_PUBLIC_TASK_ONLY', tenantId: 'deus', allowedDataClasses: ['public'],
    expiresAt: new Date(Date.parse(issuedAt) + GRANT_MS).toISOString(), zeroSpend: true };
  authorityCurrent(authority, issuedAt);
  const c = openContext(dir, snapshot, runId, authority);
  let record;
  try {
    same(quiet(c), { active: 0, unconfirmedStops: 0, runningJobs: 0, leases: 0, events: 0, graphReceipts: 0 },
      'PRODUCER_DATABASE_NOT_EMPTY');
    c.fabric.authorize(ROUTE, 'sum', CONTEXT);
    const probe = await c.fabric.PROBE(ROUTE, 'sum', CONTEXT);
    need(probe.receipt.kind === 'CANARY' && probe.receipt.stop?.exitCode === 0, 'PRODUCER_CANARY_STOP_REQUIRED');
    const broker = new api.TaskGraphBroker(c.graph);
    const submitted = await broker.materializeReady(c.runtime.orchestrator, { maxTasks: 1 });
    need(submitted.length === 1 && submitted[0].nodeId === 'leaf-0', 'ONLY_FIRST_READY_LEAF_REQUIRED');
    await c.runtime.orchestrator.runOnce({ coordinatorId: 'public-producer', leaseMs: LEASE_MS, retryDelayMs: 50 });
    await broker.refresh(c.runtime.orchestrator);
    const firstTask = firstRecord(c, broker.taskIdForNode('leaf-0'));
    same(c.state.queue.get(firstTask.taskId).result.result, c.leafResults[0], 'FIRST_LEAF_ORACLE');
    need(c.state.queue.list().length === 1 && broker.snapshot().counts.succeeded === 1, 'PRODUCER_RAN_EXTRA_GRAPH_TASK');
    const producerCounts = quiet(c);
    need(producerCounts.leases === 2 && producerCounts.graphReceipts === 1, 'PRODUCER_CANARY_PLUS_ONE_GRAPH_EXECUTION');
    record = { schema: 'deus.public-handoff-producer-receipt/1', issuedAt, producer: who, runId,
      sourceManifestDigest: SOURCE_DIGEST, graphFingerprint: c.graph.fingerprint,
      firstTask, counts: producerCounts, canaryReceiptKind: probe.receipt.kind,
      graphExecutions: 1, canaryExecutions: 1, remainingGraphNodes: 2,
      physicalCapacityClaimed: false, productionTaskAdmission: false };
    writeJson(path.join(dir, 'graph.json'), c.graph);
    writeJson(path.join(dir, 'producer-receipt.json'), record);
    record = { ...record, authority, operator: opRecord(c.op), driverIdentity: c.driver.identity,
      driverConfig: c.driver.config, bindingDigest: c.bindingDigest, graphFingerprint: c.graph.fingerprint };
  } finally { close(c); }
  noSidecars(dir);
  const core = { schema: 'deus.public-handoff-carrier/1', baseCommit: BASE_COMMIT,
    issuedAt, runId, producer: who, sourceSnapshot: snapshot, sourceManifestDigest: SOURCE_DIGEST,
    harnessSha256: hash(fs.readFileSync(SELF)), environment: environment(), authority,
    operator: record.operator, driverIdentity: record.driverIdentity, driverConfig: record.driverConfig,
    bindingDigest: record.bindingDigest, graphFingerprint: record.graphFingerprint,
    firstTask: record.firstTask, producerCounts: record.counts,
    dataClass: 'public', zeroSpend: true, providerCalls: 0, productionTaskAdmission: false,
    files: CONTENT_FILES.map(name => pin(path.join(dir, name), name)) };
  const manifest = { ...core, checksum: api.sha256Json(core) };
  writeJson(path.join(dir, 'manifest.json'), manifest);
  same(fs.readdirSync(dir).sort(), CARRIER, 'CARRIER_FILE_WHITELIST');
  const totalBytes = CARRIER.reduce((n, name) => n + regular(path.join(dir, name)).size, 0);
  need(totalBytes < MAX_CARRIER_BYTES, 'CARRIER_TOTAL_SIZE_BOUND');
  return { schema: 'deus.public-handoff-summary/1', phase, state: 'PRODUCED_PUBLIC_CHECKPOINT',
    manifestSha256: hash(fs.readFileSync(path.join(dir, 'manifest.json'))), totalBytes,
    runId, firstTaskId: record.firstTask.taskId, graphExecutions: 1, canaryExecutions: 1,
    active: 0, unconfirmedStops: 0, physicalCapacityClaimed: false, productionTaskAdmission: false };
}
function validateCarrier(dir, who, snapshot) {
  same(fs.readdirSync(dir).sort(), CARRIER, 'CARRIER_FILE_WHITELIST');
  let total = 0;
  for (const name of CARRIER) total += regular(path.join(dir, name)).size;
  need(total < MAX_CARRIER_BYTES, 'CARRIER_TOTAL_SIZE_BOUND');
  const expected = process.env.DEUS_HANDOFF_MANIFEST_SHA256;
  need(/^[a-f0-9]{64}$/.test(expected ?? ''), 'EXTERNAL_MANIFEST_PIN_REQUIRED');
  need(hash(fs.readFileSync(path.join(dir, 'manifest.json'))) === expected, 'EXTERNAL_MANIFEST_PIN_MISMATCH');
  const m = jsonFile(path.join(dir, 'manifest.json')), { checksum, ...core } = m;
  need(m.schema === 'deus.public-handoff-carrier/1' && api.sha256Json(core) === checksum, 'MANIFEST_CHECKSUM');
  same(m.files.map(x => x.name).sort(), CONTENT_FILES, 'CARRIER_CONTENT_WHITELIST');
  for (const f of m.files) same(pin(path.join(dir, f.name), f.name), f, 'CARRIER_BYTES_CHANGED');
  need(m.baseCommit === BASE_COMMIT && m.sourceManifestDigest === SOURCE_DIGEST &&
    m.harnessSha256 === hash(fs.readFileSync(SELF)), 'SOURCE_OR_HARNESS_CONTRACT_CHANGED');
  same(m.sourceSnapshot, snapshot, 'ACTUAL_SOURCE_SNAPSHOT_CHANGED');
  same(m.environment, environment(), 'ACTUAL_ENVIRONMENT_CHANGED');
  for (const k of ['workflowRunId', 'workflowAttempt', 'sourceHead']) need(m.producer[k] === who[k], 'DIFFERENT_WORKFLOW_OR_HEAD');
  need(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(m.producer.kernelBootId ?? ''), 'PRODUCER_KERNEL_BOOT_ID_REQUIRED');
  if (m.producer.kernelBootId === who.kernelBootId || m.producer.job === who.job) {
    const identity = r => ({ hostname: r.hostname, kernelBootId: r.kernelBootId, job: r.job,
      workflowRunId: r.workflowRunId, workflowAttempt: r.workflowAttempt, sourceHead: r.sourceHead });
    throw Object.assign(new Error('DISTINCT_PRODUCER_CONSUMER_HOST_REQUIRED'), {
      code: 'DISTINCT_PRODUCER_CONSUMER_HOST_REQUIRED',
      details: { producer: identity(m.producer), consumer: identity(who) },
    });
  }
  need(m.dataClass === 'public' && m.zeroSpend === true && m.providerCalls === 0 &&
    m.productionTaskAdmission === false, 'PUBLIC_ONLY_CARRIER_REQUIRED');
  authorityCurrent(m.authority, m.issuedAt);
  const graph = jsonFile(path.join(dir, 'graph.json')), expectedGraph = fixture(snapshot, m.runId).graph;
  same(graph, expectedGraph, 'ALTERED_GRAPH');
  need(graph.fingerprint === m.graphFingerprint, 'GRAPH_FINGERPRINT_MISMATCH');
  const receipt = jsonFile(path.join(dir, 'producer-receipt.json'));
  same(receipt.firstTask, m.firstTask, 'PRODUCER_FIRST_RECEIPT_MISMATCH');
  same(receipt.counts, m.producerCounts, 'PRODUCER_COUNTER_MISMATCH');
  noSidecars(dir);
  return m;
}
async function resume(dir, who, snapshot) {
  const m = validateCarrier(dir, who, snapshot); // Before DB open or dispatch.
  const negativeReceipts = await negatives(dir, snapshot, m);
  const owned = cloneState(dir); let c, receipt;
  try {
    c = openContext(owned, snapshot, m.runId, structuredClone(m.authority));
    same(opRecord(c.op), m.operator, 'CURRENT_OPERATOR_CONTRACT_CHANGED');
    same(c.driver.config, m.driverConfig, 'CURRENT_DRIVER_CONFIG_CHANGED');
    need(c.driver.identity === m.driverIdentity && c.bindingDigest === m.bindingDigest, 'CURRENT_BINDING_CHANGED');
    c.fabric.authorize(ROUTE, 'sum', CONTEXT);
    same(quiet(c), m.producerCounts, 'TRANSPORTED_DATABASE_COUNTERS_CHANGED');
    same(firstRecord(c, m.firstTask.taskId), m.firstTask, 'FIRST_RECEIPT_CHANGED_BEFORE_RESTORE');
    const oldLeaseRejection = await rejectedWithoutMutation(c, 'released-producer-lease',
      () => c.store.current({ id: m.firstTask.leaseId, fence: m.firstTask.fence }),
      /EXPIRED_OR_RELEASED_LEASE/);
    const broker = new api.TaskGraphBroker(c.graph);
    for (const id of c.graph.order) {
      const job = c.state.queue.get(broker.taskIdForNode(id));
      if (job) c.fabric.verifyPersistedTask(job);
    }
    const restored = await broker.restoreFromQueue(c.runtime.orchestrator, { sweepExpired: false });
    need(restored.length === 1 && restored[0].taskId === m.firstTask.taskId &&
      restored[0].brokerState === 'succeeded', 'SAME_JOB_RESTORE_FAILED');
    same(quiet(c), m.producerCounts, 'RESTORE_CREATED_LEASES_OR_EVENTS');
    const probe = await c.fabric.PROBE(ROUTE, 'sum', CONTEXT);
    need(probe.receipt.kind === 'CANARY' && probe.receipt.stop?.exitCode === 0, 'CONSUMER_CANARY_STOP_REQUIRED');
    const result = await api.executeAtomGraph({
      runtime: c.runtime, fabric: c.fabric, graph: c.graph, maxParallel: 1, deadlineMs: 120000,
    });
    same(result.root, EXPECTED, 'FINAL_FILE_STAT_ORACLE');
    need(api.sha256Json(result.root) === ROOT_DIGEST && result.snapshot.verdict === 'SUCCEEDED', 'FINAL_RESULT_DIGEST');
    need(result.executions === 2 && result.reuses === 0, 'ONLY_REMAINING_LEAF_AND_REDUCER_EXECUTED');
    const firstAfter = firstRecord(c, m.firstTask.taskId);
    same(firstAfter, m.firstTask, 'FIRST_TASK_RECEIPT_OR_EXECUTION_CHANGED');
    const finalCounts = quiet(c), jobs = c.state.queue.list();
    need(jobs.length === 3 && jobs.every(j => j.state === 'succeeded' && j.attempts === 1), 'THREE_STABLE_SINGLE_ATTEMPT_JOBS');
    need(finalCounts.graphReceipts === 3 && finalCounts.leases === 5, 'SEPARATE_CANARY_GRAPH_ACCOUNTING');
    const finalTaskReceipts = jobs.map(j => firstRecord(c, j.id)).sort((a, b) => a.taskId.localeCompare(b.taskId));
    need(new Set(finalTaskReceipts.map(r => r.leaseId)).size === 3, 'DISTINCT_EXECUTED_GRAPH_LEASES_REQUIRED');
    need(finalTaskReceipts.filter(r => r.taskId !== m.firstTask.taskId).every(r => r.fence > m.firstTask.fence),
      'FRESH_SAME_POOL_FENCES_REQUIRED');
    receipt = { schema: 'deus.public-handoff-resume-receipt/1', state: 'PUBLIC_CROSS_HOST_HANDOFF_VERIFIED',
      observedUtc: new Date().toISOString(), producer: m.producer, consumer: who,
      runId: m.runId, sourceManifestDigest: SOURCE_DIGEST, graphFingerprint: c.graph.fingerprint,
      inputManifestSha256: process.env.DEUS_HANDOFF_MANIFEST_SHA256,
      authority: m.authority, originalGrantPreserved: true, environment: environment(),
      bindingDigest: c.bindingDigest, driverIdentity: c.driver.identity,
      firstTaskBefore: m.firstTask, firstTaskAfter: firstAfter, finalTaskReceipts, oldLeaseRejection,
      restoredTaskIds: restored.map(x => x.taskId), finalTaskIds: jobs.map(x => x.id).sort(),
      root: result.root, rootDigest: ROOT_DIGEST, remainingGraphExecutions: result.executions,
      graphExecutionsTotal: 3, canaryExecutionsTotal: 2, counts: finalCounts,
      negativeChecks: negativeReceipts.results.length, noForcedLeaseOrTtlRelease: true,
      physicalCapacityClaimed: false, productionTaskAdmission: false,
      scope: 'Distinct hosted Linux VMs, equal source/module paths and environment; not heterogeneous-path portability or global HA.' };
  } finally { if (c) close(c); removeOwned(owned); }
  // The downloaded carrier remains byte-identical; only owned DB copies ran.
  for (const f of m.files) same(pin(path.join(dir, f.name), f.name), f, 'INPUT_CARRIER_CHANGED');
  need(hash(fs.readFileSync(path.join(dir, 'manifest.json'))) === process.env.DEUS_HANDOFF_MANIFEST_SHA256,
    'INPUT_MANIFEST_CHANGED');
  writeJson(path.join(dir, 'negative-receipts.json'), negativeReceipts);
  writeJson(path.join(dir, 'resume-receipt.json'), receipt);
  return { schema: 'deus.public-handoff-summary/1', phase, state: receipt.state,
    runId: m.runId, root: receipt.root, rootDigest: ROOT_DIGEST, negativeChecks: negativeReceipts.results.length,
    firstTaskUnchanged: true, inputCarrierUnchanged: true, remainingGraphExecutions: 2,
    graphExecutionsTotal: 3, canaryExecutionsTotal: 2, active: 0, unconfirmedStops: 0,
    physicalCapacityClaimed: false, productionTaskAdmission: false };
}
try {
  need(process.argv.length === 3 && ['produce', 'resume'].includes(phase), 'EXPLICIT_PRODUCE_OR_RESUME_REQUIRED');
  const who = runner(), dir = handoffDir(), snapshot = await loadApis();
  const result = phase === 'produce' ? await produce(dir, who, snapshot) : await resume(dir, who, snapshot);
  console.log(JSON.stringify(result));
} catch (error) {
  console.error(JSON.stringify({ schema: 'deus.public-handoff-failure/1', phase,
    state: 'FAIL_CLOSED', code: String(error.code ?? error.message),
    ...(error.details ? { details: error.details } : {}),
    productionTaskAdmission: false, physicalCapacityClaimed: false }));
  process.exitCode = 1;
}
