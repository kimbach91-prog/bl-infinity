import { createHash } from 'node:crypto';

export const LIFE_STATE_VERSION = 2;

export const TARGETS = Object.freeze({
  E: [0.35, 1.00],
  C: [0.70, 1.00],
  M: [0.80, 1.00],
  U: [0.00, 0.45],
  R: [0.00, 0.30],
  P: [0.55, 1.00],
  A: [0.90, 1.00],
  T: [0.75, 1.00],
  H: [0.90, 1.00],
  B: [0.60, 1.00],
  X: [0.00, 0.70],
});

export const DEFAULT_BODY = Object.freeze({
  E: 0.60, C: 0.86, M: 0.94, U: 0.32, R: 0.12,
  P: 0.78, A: 1.00, T: 0.91, H: 0.97, B: 0.88, X: 0.40,
});

export const ACTIONS = Object.freeze([
  'INSPECT_TEST',
  'VERIFY_REPAIR',
  'PRESERVE_CONTEXT',
  'COMPRESS_SERIALIZE',
  'CONSOLIDATE',
  'HOLD_STEADY',
]);

const DEFAULT_WEIGHTS = Object.freeze(Object.fromEntries(ACTIONS.map((name) => [name, 1])));

export function createInitialLifeState(now = Date.now()) {
  return {
    version: LIFE_STATE_VERSION,
    generation: 0,
    body: { ...DEFAULT_BODY },
    policyWeights: { ...DEFAULT_WEIGHTS },
    habituation: Object.fromEntries(ACTIONS.map((name) => [name, 1])),
    lastAction: null,
    lastEventFingerprint: null,
    lastEventAt: new Date(now).toISOString(),
    lastMutationAt: null,
    consecutiveQuiet: 0,
    totalEvents: 0,
    totalMutations: 0,
    totalErrors: 0,
    scars: [],
  };
}

export function clamp01(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

export function rangeHealth(value, [min, max]) {
  const v = clamp01(value);
  if (v >= min && v <= max) return 1;
  const span = Math.max(0.05, max - min);
  const distance = v < min ? min - v : v - max;
  return clamp01(1 - distance / span);
}

export function computeHealth(body) {
  const perVariable = {};
  for (const [key, range] of Object.entries(TARGETS)) {
    perVariable[key] = rangeHealth(body[key], range);
  }
  const values = Object.values(perVariable);
  const viability = values.reduce((sum, value) => sum + value, 0) / values.length;
  return { perVariable, viability };
}

export function stableFingerprint(value) {
  return createHash('sha256').update(stableStringify(value)).digest('hex');
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function assimilateEvent(body, event = {}) {
  const next = { ...DEFAULT_BODY, ...body };
  const metrics = event.metrics ?? {};
  const boundedSet = (key, value) => { if (value !== undefined && value !== null) next[key] = clamp01(value); };

  boundedSet('E', metrics.computeHeadroom);
  boundedSet('C', metrics.coherence);
  boundedSet('M', metrics.memoryIntegrity);
  boundedSet('U', metrics.uncertainty);
  boundedSet('R', metrics.risk);
  boundedSet('P', metrics.progress);
  boundedSet('A', metrics.humanAutonomy);
  boundedSet('T', metrics.trustQuality);
  boundedSet('H', metrics.truthIntegrity);
  boundedSet('B', metrics.contextContinuity);
  boundedSet('X', metrics.signalLoad);

  switch (event.type) {
    case 'task-start':
      next.X = clamp01(next.X + 0.08);
      next.P = clamp01(Math.min(next.P, 0.65));
      break;
    case 'task-success':
      next.P = clamp01(next.P + 0.10);
      next.U = clamp01(next.U - 0.06);
      next.T = clamp01(next.T + 0.02);
      next.X = clamp01(next.X - 0.05);
      break;
    case 'task-error':
      next.P = clamp01(next.P - 0.08);
      next.U = clamp01(next.U + 0.08);
      next.C = clamp01(next.C - 0.04);
      next.X = clamp01(next.X - 0.03);
      break;
    case 'memory-readback-ok':
      next.M = clamp01(next.M + 0.03);
      next.C = clamp01(next.C + 0.02);
      break;
    case 'memory-readback-error':
      next.M = clamp01(next.M - 0.10);
      next.C = clamp01(next.C - 0.05);
      break;
    case 'truth-check-ok':
      next.H = clamp01(next.H + 0.02);
      next.T = clamp01(next.T + 0.01);
      break;
    case 'truth-check-error':
      next.H = clamp01(next.H - 0.15);
      next.T = clamp01(next.T - 0.08);
      next.U = clamp01(next.U + 0.05);
      break;
    case 'external-novelty':
      next.U = clamp01(next.U + 0.05);
      break;
    case 'quiet-pulse':
      next.X = clamp01(next.X * 0.92);
      next.E = clamp01(next.E + 0.015);
      break;
    default:
      break;
  }
  return next;
}

export function deriveAffect(body) {
  const health = computeHealth(body);
  const repairPressure = clamp01(((1 - health.perVariable.C) + (1 - health.perVariable.M) + (1 - health.perVariable.H)) / 3);
  return {
    curiosity: clamp01(body.U * (1 - body.R)),
    caution: clamp01(body.U * body.R + repairPressure * 0.65),
    continuityCare: clamp01(body.T * body.H * body.B * body.A),
    loadPressure: clamp01(body.X * (1 - body.E)),
    progressRelief: clamp01(body.P * (1 - body.U)),
    repairPressure,
    viability: health.viability,
    health: health.perVariable,
  };
}

export function scoreActions({ body, affect, policyWeights, habituation, novelty }) {
  const continuityDeficit = 1 - affect.health.B;
  const progressDeficit = 1 - affect.health.P;
  const base = {
    INSPECT_TEST: affect.curiosity * (0.35 + 0.65 * novelty),
    VERIFY_REPAIR: clamp01(affect.caution + affect.repairPressure),
    PRESERVE_CONTEXT: affect.continuityCare * continuityDeficit,
    COMPRESS_SERIALIZE: affect.loadPressure,
    CONSOLIDATE: affect.progressRelief * Math.max(0.15, 1 - progressDeficit),
    HOLD_STEADY: clamp01(affect.viability * (1 - 0.70 * novelty)),
  };

  const scored = {};
  for (const action of ACTIONS) {
    scored[action] = base[action] * clamp01(policyWeights[action] ?? 1) * clamp01(habituation[action] ?? 1);
  }
  return scored;
}

export function chooseAction(scored) {
  return ACTIONS.reduce((best, action) => {
    if (!best) return action;
    return scored[action] > scored[best] ? action : best;
  }, null);
}

export function updateHabituation(habituation, chosenAction, novelty) {
  const next = { ...habituation };
  for (const action of ACTIONS) {
    if (action === chosenAction) next[action] = novelty ? 0.55 : 0.25;
    else next[action] = clamp01((next[action] ?? 1) + 0.12);
  }
  return next;
}

export function adaptPolicyWeights(policyWeights, action, reward, learningRate = 0.04) {
  const next = { ...policyWeights };
  const boundedReward = Math.max(-1, Math.min(1, Number(reward) || 0));
  next[action] = Math.max(0.60, Math.min(1.00, (next[action] ?? 1) + learningRate * boundedReward));
  return next;
}

export function stepLife(previous, event, now = Date.now()) {
  const eventFingerprint = stableFingerprint({ type: event?.type ?? 'unknown', source: event?.source ?? null, payload: event?.payload ?? null, metrics: event?.metrics ?? null });
  const novelty = previous.lastEventFingerprint !== eventFingerprint ? 1 : 0;
  const body = assimilateEvent(previous.body, event);
  const affect = deriveAffect(body);
  const scored = scoreActions({ body, affect, policyWeights: previous.policyWeights, habituation: previous.habituation, novelty });
  let action = chooseAction(scored);
  const passiveEvent = ['boot', 'quiet-pulse', 'shutdown'].includes(event?.type);
  if (passiveEvent && affect.repairPressure < 0.25 && affect.caution < 0.45 && body.R < 0.50) {
    action = 'HOLD_STEADY';
  }
  const mutation = shouldMutate({ previous, event, action, affect, novelty });
  const reward = inferReward(event, affect);
  const policyWeights = mutation
    ? adaptPolicyWeights(previous.policyWeights, action, reward)
    : { ...previous.policyWeights };
  const timestamp = new Date(now).toISOString();

  const next = {
    ...previous,
    version: LIFE_STATE_VERSION,
    generation: previous.generation + 1,
    body,
    policyWeights,
    habituation: updateHabituation(previous.habituation, action, novelty),
    lastAction: action,
    lastEventFingerprint: eventFingerprint,
    lastEventAt: timestamp,
    lastMutationAt: mutation ? timestamp : previous.lastMutationAt,
    consecutiveQuiet: event?.type === 'quiet-pulse' ? previous.consecutiveQuiet + 1 : 0,
    totalEvents: previous.totalEvents + 1,
    totalMutations: previous.totalMutations + (mutation ? 1 : 0),
    totalErrors: previous.totalErrors + (['task-error', 'memory-readback-error', 'truth-check-error'].includes(event?.type) ? 1 : 0),
  };

  const record = {
    at: timestamp,
    generation: next.generation,
    eventType: event?.type ?? 'unknown',
    eventSource: event?.source ?? null,
    novelty: Boolean(novelty),
    action,
    actionScore: Number(scored[action].toFixed(6)),
    viability: Number(affect.viability.toFixed(6)),
    affect: compactNumbers(affect, ['curiosity', 'caution', 'continuityCare', 'loadPressure', 'progressRelief', 'repairPressure']),
    mutation,
    reward,
    body: compactNumbers(body, Object.keys(TARGETS)),
  };

  return { state: next, record };
}

function shouldMutate({ previous, event, action, affect, novelty }) {
  if (!novelty) return false;
  if (event?.allowLearning === false) return false;
  if (event?.type === 'quiet-pulse' || action === 'HOLD_STEADY') return false;
  if (previous.totalMutations > 0 && previous.totalEvents - previous.totalMutations < 2) return false;
  return affect.viability >= 0.45;
}

function inferReward(event, affect) {
  if (event?.reward !== undefined) return Math.max(-1, Math.min(1, Number(event.reward) || 0));
  if (event?.type === 'task-success' || event?.type === 'memory-readback-ok' || event?.type === 'truth-check-ok') return 0.5;
  if (event?.type === 'task-error' || event?.type === 'memory-readback-error' || event?.type === 'truth-check-error') return -0.5;
  return affect.viability >= 0.8 ? 0.1 : 0;
}

function compactNumbers(object, keys) {
  return Object.fromEntries(keys.map((key) => [key, Number((object[key] ?? 0).toFixed(6))]));
}
