import { randomUUID } from 'node:crypto';

const DIMENSIONS = Object.freeze([
  'energyJoules',
  'costUsd',
  'acceleratorSeconds',
  'tokens',
  'wallTimeMs',
]);

export const COMPUTE_TIERS = Object.freeze(['T0', 'T1', 'T2', 'T3', 'T4', 'T5']);

const DEFAULT_LIMITS = Object.freeze({
  energyJoules: Infinity,
  costUsd: Infinity,
  acceleratorSeconds: Infinity,
  tokens: Infinity,
  wallTimeMs: Infinity,
});

function finiteOrInfinity(value, name) {
  if (value === Infinity || value == null) return Infinity;
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) throw new Error(`${name} must be >= 0 or Infinity`);
  return n;
}

function nonNegative(value, name) {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n) || n < 0) throw new Error(`${name} must be a non-negative finite number`);
  return n;
}

function normalizeVector(input = {}, { limits = false } = {}) {
  return Object.fromEntries(DIMENSIONS.map((key) => [
    key,
    limits ? finiteOrInfinity(input[key], key) : nonNegative(input[key], key),
  ]));
}

function add(a, b) {
  return Object.fromEntries(DIMENSIONS.map((key) => [key, a[key] + b[key]]));
}

function sub(a, b) {
  return Object.fromEntries(DIMENSIONS.map((key) => [key, Math.max(0, a[key] - b[key])]));
}

function exceeds(used, delta, limits) {
  for (const key of DIMENSIONS) {
    if (used[key] + delta[key] > limits[key] + 1e-12) return key;
  }
  return null;
}

function tierIndex(tier) {
  const index = COMPUTE_TIERS.indexOf(tier);
  if (index < 0) throw new Error(`unknown compute tier: ${tier}`);
  return index;
}

function clone(value) {
  return structuredClone(value);
}

export class ResourceEnvelopeGovernor {
  constructor({ globalLimits = {} } = {}) {
    this.globalLimits = normalizeVector({ ...DEFAULT_LIMITS, ...globalLimits }, { limits: true });
    this.globalSpent = normalizeVector();
    this.globalReserved = normalizeVector();
    this.tasks = new Map();
    this.reservations = new Map();
  }

  openTask({
    taskId,
    tenantId = 'default',
    purpose = null,
    authority = null,
    dataResidency = [],
    limits = {},
    tierCeiling = 'T4',
    assuranceLevel = 'medium',
    catastrophicRiskClass = 0,
  } = {}) {
    if (!taskId || typeof taskId !== 'string') throw new Error('taskId is required');
    if (this.tasks.has(taskId)) throw new Error(`task already exists: ${taskId}`);
    const risk = Number(catastrophicRiskClass);
    if (!Number.isInteger(risk) || risk < 0 || risk > 4) throw new Error('catastrophicRiskClass must be an integer from 0 to 4');
    if (tierCeiling === 'T5') throw new Error('T5 cannot be a default task tier ceiling; HPC requires explicit authorization');
    tierIndex(tierCeiling);

    const task = {
      taskId,
      tenantId,
      purpose,
      authority,
      dataResidency: [...dataResidency],
      assuranceLevel,
      catastrophicRiskClass: risk,
      tierCeiling,
      limits: normalizeVector({ ...DEFAULT_LIMITS, ...limits }, { limits: true }),
      spent: normalizeVector(),
      reserved: normalizeVector(),
      state: 'open',
      openedAt: new Date().toISOString(),
    };
    this.tasks.set(taskId, task);
    return clone(task);
  }

  authorize(taskId, estimate = {}, { tier = 'T0', explicitHpcAuthorization = false } = {}) {
    const task = this.#openTask(taskId);
    const requestedTier = String(tier);
    const requestedTierIndex = tierIndex(requestedTier);
    if (requestedTier === 'T5' && !explicitHpcAuthorization) {
      return { ok: false, reason: 't5-explicit-authorization-required' };
    }
    if (requestedTier !== 'T5' && requestedTierIndex > tierIndex(task.tierCeiling)) {
      return { ok: false, reason: 'task-tier-ceiling-exceeded' };
    }

    const vector = normalizeVector(estimate);
    const taskBreach = exceeds(add(task.spent, task.reserved), vector, task.limits);
    if (taskBreach) return { ok: false, reason: `task-${taskBreach}-limit-exceeded`, dimension: taskBreach };
    const globalBreach = exceeds(add(this.globalSpent, this.globalReserved), vector, this.globalLimits);
    if (globalBreach) return { ok: false, reason: `global-${globalBreach}-limit-exceeded`, dimension: globalBreach };

    const id = randomUUID();
    const reservation = {
      id,
      taskId,
      tenantId: task.tenantId,
      tier: requestedTier,
      estimate: vector,
      state: 'reserved',
      explicitHpcAuthorization: Boolean(explicitHpcAuthorization),
      createdAt: new Date().toISOString(),
    };
    task.reserved = add(task.reserved, vector);
    this.globalReserved = add(this.globalReserved, vector);
    this.reservations.set(id, reservation);
    return { ok: true, reservation: clone(reservation) };
  }

  commit(reservationId, actual = null) {
    const reservation = this.#activeReservation(reservationId);
    const task = this.#openTask(reservation.taskId);
    const vector = actual == null ? reservation.estimate : normalizeVector(actual);

    const taskWithoutReservation = sub(task.reserved, reservation.estimate);
    const globalWithoutReservation = sub(this.globalReserved, reservation.estimate);

    const taskBreach = exceeds(add(task.spent, taskWithoutReservation), vector, task.limits);
    if (taskBreach) throw Object.assign(new Error(`actual usage rejected: task-${taskBreach}-limit-exceeded`), { code: 'RESOURCE_ENVELOPE_EXCEEDED', dimension: taskBreach });
    const globalBreach = exceeds(add(this.globalSpent, globalWithoutReservation), vector, this.globalLimits);
    if (globalBreach) throw Object.assign(new Error(`actual usage rejected: global-${globalBreach}-limit-exceeded`), { code: 'RESOURCE_ENVELOPE_EXCEEDED', dimension: globalBreach });

    task.reserved = taskWithoutReservation;
    this.globalReserved = globalWithoutReservation;
    task.spent = add(task.spent, vector);
    this.globalSpent = add(this.globalSpent, vector);
    reservation.state = 'committed';
    reservation.actual = vector;
    reservation.committedAt = new Date().toISOString();
    return clone(reservation);
  }

  release(reservationId, reason = 'released') {
    const reservation = this.#activeReservation(reservationId);
    const task = this.#openTask(reservation.taskId);
    task.reserved = sub(task.reserved, reservation.estimate);
    this.globalReserved = sub(this.globalReserved, reservation.estimate);
    reservation.state = 'released';
    reservation.releaseReason = reason;
    reservation.releasedAt = new Date().toISOString();
    return clone(reservation);
  }

  closeTask(taskId, reason = 'completed') {
    const task = this.#openTask(taskId);
    if (DIMENSIONS.some((key) => task.reserved[key] > 1e-12)) throw new Error('cannot close task with active reservations');
    task.state = 'closed';
    task.closeReason = reason;
    task.closedAt = new Date().toISOString();
    return clone(task);
  }

  taskSnapshot(taskId) {
    const task = this.tasks.get(taskId);
    if (!task) throw new Error(`unknown task: ${taskId}`);
    return clone(task);
  }

  snapshot() {
    return {
      dimensions: [...DIMENSIONS],
      globalLimits: clone(this.globalLimits),
      globalSpent: clone(this.globalSpent),
      globalReserved: clone(this.globalReserved),
      openTasks: [...this.tasks.values()].filter((x) => x.state === 'open').length,
      activeReservations: [...this.reservations.values()].filter((x) => x.state === 'reserved').length,
    };
  }

  #openTask(taskId) {
    const task = this.tasks.get(taskId);
    if (!task) throw new Error(`unknown task: ${taskId}`);
    if (task.state !== 'open') throw new Error(`task is ${task.state}: ${taskId}`);
    return task;
  }

  #activeReservation(id) {
    const reservation = this.reservations.get(id);
    if (!reservation) throw new Error(`unknown reservation: ${id}`);
    if (reservation.state !== 'reserved') throw new Error(`reservation is ${reservation.state}`);
    return reservation;
  }
}

export function chooseComputeTier({
  cacheHit = false,
  deterministicAvailable = false,
  edgeEligible = false,
  specialistAvailable = true,
  independentVerificationRequired = false,
  assuranceLevel = 'medium',
  uncertainty = 0.5,
  novelty = 0.5,
  catastrophicRiskClass = 0,
} = {}) {
  if (cacheHit || deterministicAvailable) return { tier: 'T0', reason: cacheHit ? 'reuse-hit' : 'deterministic-tool-available' };
  if (edgeEligible && uncertainty <= 0.25 && novelty <= 0.25 && catastrophicRiskClass <= 1) return { tier: 'T1', reason: 'edge-sufficient' };
  if (independentVerificationRequired || catastrophicRiskClass >= 3 || assuranceLevel === 'critical') return { tier: 'T3', reason: 'independent-verification-required' };
  if (specialistAvailable && uncertainty <= 0.6 && novelty <= 0.6) return { tier: 'T2', reason: 'specialist-sufficient' };
  return { tier: 'T4', reason: 'novel-or-high-uncertainty' };
}

export function evaluateStop({
  quality = 0,
  minimumQuality = 1,
  verificationConverged = false,
  newMaterialEvidence = true,
  marginalQualityGain = null,
  marginalEnergyJoules = null,
  minimumGainPerJoule = 0,
  recommendedActionChanged = true,
  safetyRisk = 0,
  expectedBenefit = Infinity,
} = {}) {
  if (quality >= minimumQuality) return { stop: true, reason: 'required-quality-reached' };
  if (verificationConverged) return { stop: true, reason: 'verification-converged' };
  if (!newMaterialEvidence) return { stop: true, reason: 'no-material-new-evidence' };
  if (!recommendedActionChanged) return { stop: true, reason: 'recommended-action-stable' };
  if (Number(safetyRisk) > Number(expectedBenefit)) return { stop: true, reason: 'safety-risk-exceeds-benefit' };
  if (marginalQualityGain != null && marginalEnergyJoules != null) {
    const gain = nonNegative(marginalQualityGain, 'marginalQualityGain');
    const joules = nonNegative(marginalEnergyJoules, 'marginalEnergyJoules');
    const floor = nonNegative(minimumGainPerJoule, 'minimumGainPerJoule');
    const ratio = joules === 0 ? Infinity : gain / joules;
    if (ratio < floor) return { stop: true, reason: 'marginal-gain-per-joule-below-threshold', gainPerJoule: ratio };
  }
  return { stop: false, reason: 'continue' };
}
