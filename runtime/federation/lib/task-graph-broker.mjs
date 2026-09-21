import { sha256Json } from './canonical.mjs';

const MAX_GRAPH_NODES = 10_000;

function requiredString(value, name) {
  const text = String(value ?? '').trim();
  if (!text) throw new Error(`${name} is required`);
  return text;
}

function nonNegative(value, name, fallback = 0) {
  const n = Number(value ?? fallback);
  if (!Number.isFinite(n) || n < 0) throw new Error(`${name} must be a non-negative number`);
  return n;
}

function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

function normalizeNode(raw, graphDefaults) {
  const id = requiredString(raw?.id, 'node.id');
  const capability = requiredString(raw?.capability, `node.${id}.capability`);
  const deps = [...new Set((raw?.deps ?? []).map((x) => requiredString(x, `node.${id}.deps[]`)))];
  if (deps.includes(id)) throw new Error(`node cannot depend on itself: ${id}`);
  return Object.freeze({
    id,
    capability,
    deps: Object.freeze(deps),
    payload: clone(raw?.payload ?? null),
    dataClass: String(raw?.dataClass ?? graphDefaults.dataClass ?? 'public'),
    dataLocation: raw?.dataLocation ?? graphDefaults.dataLocation ?? null,
    estimatedCostUsd: nonNegative(raw?.estimatedCostUsd, `node.${id}.estimatedCostUsd`, 0),
    cacheTtlMs: raw?.cacheTtlMs == null ? graphDefaults.cacheTtlMs ?? null : nonNegative(raw.cacheTtlMs, `node.${id}.cacheTtlMs`),
    priority: Number(raw?.priority ?? graphDefaults.priority ?? 0) || 0,
    sideEffect: raw?.sideEffect === true,
    retrySafe: raw?.retrySafe === true,
    injectUpstreamResults: raw?.injectUpstreamResults !== false,
    virtualWorkUnits: raw?.virtualWorkUnits == null ? null : String(raw.virtualWorkUnits),
    tags: Object.freeze([...(raw?.tags ?? [])].map(String)),
  });
}

function topologicalOrder(nodes) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  for (const node of nodes) {
    for (const dep of node.deps) {
      if (!byId.has(dep)) throw new Error(`unknown dependency ${dep} for node ${node.id}`);
    }
  }

  const indegree = new Map(nodes.map((n) => [n.id, n.deps.length]));
  const children = new Map(nodes.map((n) => [n.id, []]));
  for (const node of nodes) for (const dep of node.deps) children.get(dep).push(node.id);

  const ready = [...nodes.filter((n) => indegree.get(n.id) === 0).map((n) => n.id)].sort();
  const order = [];
  while (ready.length) {
    const id = ready.shift();
    order.push(id);
    for (const child of children.get(id)) {
      const next = indegree.get(child) - 1;
      indegree.set(child, next);
      if (next === 0) {
        ready.push(child);
        ready.sort();
      }
    }
  }
  if (order.length !== nodes.length) throw new Error('task graph contains a cycle');
  return order;
}

export function normalizeTaskGraph(graph = {}) {
  const graphId = requiredString(graph.graphId ?? graph.id, 'graphId');
  if (!Array.isArray(graph.nodes) || graph.nodes.length === 0) throw new Error('graph.nodes must be a non-empty array');
  if (graph.nodes.length > MAX_GRAPH_NODES) throw new Error(`graph.nodes exceeds ${MAX_GRAPH_NODES}`);

  const defaults = {
    dataClass: graph.dataClass ?? 'public',
    dataLocation: graph.dataLocation ?? null,
    cacheTtlMs: graph.cacheTtlMs ?? null,
    priority: graph.priority ?? 0,
  };
  const nodes = graph.nodes.map((node) => normalizeNode(node, defaults));
  const ids = nodes.map((n) => n.id);
  if (new Set(ids).size !== ids.length) throw new Error('graph node ids must be unique');
  const order = topologicalOrder(nodes);
  const normalized = {
    schema: 'deus-task-graph/1',
    graphId,
    dataClass: String(defaults.dataClass),
    dataLocation: defaults.dataLocation,
    failClosed: graph.failClosed !== false,
    nodes,
    order,
    metadata: clone(graph.metadata ?? {}),
  };
  return Object.freeze({
    ...normalized,
    fingerprint: sha256Json({
      schema: normalized.schema,
      graphId: normalized.graphId,
      dataClass: normalized.dataClass,
      dataLocation: normalized.dataLocation,
      failClosed: normalized.failClosed,
      nodes: normalized.nodes,
      metadata: normalized.metadata,
    }),
  });
}

function initialNodeState() {
  return { state: 'pending', taskId: null, result: null, resultDigest: null, error: null, submittedAt: null, finishedAt: null };
}

function statusCounts(states) {
  const counts = { pending: 0, submitted: 0, succeeded: 0, failed: 0, blocked: 0 };
  for (const value of states.values()) {
    if (Object.hasOwn(counts, value.state)) counts[value.state] += 1;
  }
  return counts;
}

export class TaskGraphBroker {
  constructor(graph) {
    this.graph = normalizeTaskGraph(graph);
    this.nodes = new Map(this.graph.nodes.map((node) => [node.id, node]));
    this.state = new Map(this.graph.nodes.map((node) => [node.id, initialNodeState()]));
  }

  readyNodeIds() {
    const out = [];
    for (const id of this.graph.order) {
      const node = this.nodes.get(id);
      const current = this.state.get(id);
      if (current.state !== 'pending') continue;
      const deps = node.deps.map((dep) => this.state.get(dep));
      if (deps.some((dep) => dep.state === 'failed' || dep.state === 'blocked')) {
        if (this.graph.failClosed) current.state = 'blocked';
        continue;
      }
      if (deps.every((dep) => dep.state === 'succeeded')) out.push(id);
    }
    return out;
  }

  buildTask(nodeId) {
    const node = this.nodes.get(nodeId);
    if (!node) throw new Error(`unknown graph node: ${nodeId}`);

    const upstream = {};
    const upstreamDigests = {};
    for (const dep of node.deps) {
      const state = this.state.get(dep);
      if (state.state !== 'succeeded') throw new Error(`dependency not satisfied: ${dep}`);
      upstream[dep] = clone(state.result);
      upstreamDigests[dep] = state.resultDigest;
    }

    const payload = node.injectUpstreamResults
      ? { input: clone(node.payload), upstream, graph: { graphId: this.graph.graphId, nodeId, graphFingerprint: this.graph.fingerprint } }
      : clone(node.payload);

    const dependencyFingerprint = sha256Json(upstreamDigests);
    return {
      id: `${this.graph.graphId}::${nodeId}`,
      tenantId: 'deus',
      capability: node.capability,
      payload,
      dataClass: node.dataClass,
      dataLocation: node.dataLocation,
      estimatedCostUsd: node.estimatedCostUsd,
      cacheTtlMs: node.cacheTtlMs,
      sideEffect: node.sideEffect,
      retrySafe: node.retrySafe,
      idempotencyKey: `graph:${this.graph.fingerprint}:node:${nodeId}:deps:${dependencyFingerprint}`,
      metadata: {
        graphId: this.graph.graphId,
        graphFingerprint: this.graph.fingerprint,
        nodeId,
        deps: [...node.deps],
        virtualWorkUnits: node.virtualWorkUnits,
        tags: [...node.tags],
      },
    };
  }

  async materializeReady(orchestrator, { maxTasks = Infinity, now = Date.now() } = {}) {
    if (!orchestrator?.submit) throw new Error('orchestrator.submit is required');
    const ready = this.readyNodeIds().slice(0, Math.max(0, Number(maxTasks) || 0));
    const submitted = [];
    for (const nodeId of ready) {
      const node = this.nodes.get(nodeId);
      const task = this.buildTask(nodeId);
      const response = await orchestrator.submit(task, { priority: node.priority });
      const state = this.state.get(nodeId);
      state.state = 'submitted';
      state.taskId = response.job.id;
      state.submittedAt = new Date(now).toISOString();
      submitted.push({ nodeId, taskId: response.job.id, deduplicated: response.deduplicated === true });
    }
    return submitted;
  }

  async refresh(orchestrator, { now = Date.now() } = {}) {
    if (!orchestrator?.queue?.get) throw new Error('orchestrator.queue.get is required');
    const changed = [];
    for (const nodeId of this.graph.order) {
      const state = this.state.get(nodeId);
      if (state.state !== 'submitted' || !state.taskId) continue;
      const job = await orchestrator.queue.get(state.taskId);
      if (!job) continue;
      if (job.state === 'succeeded') {
        const execution = job.result;
        const result = execution && typeof execution === 'object' && Object.hasOwn(execution, 'result')
          ? execution.result
          : execution;
        state.state = 'succeeded';
        state.result = clone(result);
        state.resultDigest = sha256Json(result);
        state.finishedAt = new Date(now).toISOString();
        changed.push({ nodeId, state: 'succeeded', resultDigest: state.resultDigest });
      } else if (job.state === 'deadletter') {
        state.state = 'failed';
        state.error = clone(job.error ?? { message: 'deadletter' });
        state.finishedAt = new Date(now).toISOString();
        changed.push({ nodeId, state: 'failed', error: state.error });
      }
    }
    this.readyNodeIds();
    return changed;
  }

  async advance(orchestrator, options = {}) {
    const refreshed = await this.refresh(orchestrator, options);
    const submitted = await this.materializeReady(orchestrator, options);
    return { refreshed, submitted, snapshot: this.snapshot() };
  }

  snapshot() {
    const states = Object.fromEntries(this.graph.order.map((id) => [id, clone(this.state.get(id))]));
    const counts = statusCounts(this.state);
    const terminal = counts.pending + counts.submitted === 0;
    const verdict = counts.failed + counts.blocked > 0
      ? (terminal ? 'FAILED' : 'DEGRADED')
      : (counts.succeeded === this.graph.nodes.length ? 'SUCCEEDED' : 'IN_PROGRESS');
    return {
      schema: 'deus-task-graph-broker-snapshot/1',
      graphId: this.graph.graphId,
      graphFingerprint: this.graph.fingerprint,
      nodeCount: this.graph.nodes.length,
      counts,
      verdict,
      ready: this.readyNodeIds(),
      states,
      truthBoundary: 'GRAPH_READY_OR_SUBMITTED_NE_EXECUTED__QUEUE_SUCCESS_NE_GLOBAL_VERIFIED_DONE_UNLESS_REDUCER_AND_ACCEPTANCE_NODES_PASS',
    };
  }
}

export function compileScatterReduceGraph({
  graphId,
  scatter,
  reducer,
  finalizer = null,
  dataClass = 'public',
  metadata = {},
} = {}) {
  if (!Array.isArray(scatter) || scatter.length === 0) throw new Error('scatter must be non-empty');
  const nodes = scatter.map((item, index) => ({
    id: requiredString(item.id ?? `scatter-${index + 1}`, 'scatter.id'),
    capability: requiredString(item.capability, 'scatter.capability'),
    payload: clone(item.payload ?? null),
    deps: [...(item.deps ?? [])],
    priority: item.priority ?? 0,
    estimatedCostUsd: item.estimatedCostUsd ?? 0,
    cacheTtlMs: item.cacheTtlMs ?? null,
    virtualWorkUnits: item.virtualWorkUnits ?? null,
    tags: ['scatter', ...(item.tags ?? [])],
  }));
  const scatterIds = nodes.map((node) => node.id);
  nodes.push({
    id: requiredString(reducer?.id ?? 'reduce', 'reducer.id'),
    capability: requiredString(reducer?.capability, 'reducer.capability'),
    payload: clone(reducer?.payload ?? null),
    deps: reducer?.deps ?? scatterIds,
    priority: reducer?.priority ?? 0,
    estimatedCostUsd: reducer?.estimatedCostUsd ?? 0,
    cacheTtlMs: reducer?.cacheTtlMs ?? null,
    tags: ['reduce', ...(reducer?.tags ?? [])],
  });
  if (finalizer) {
    nodes.push({
      id: requiredString(finalizer.id ?? 'finalize', 'finalizer.id'),
      capability: requiredString(finalizer.capability, 'finalizer.capability'),
      payload: clone(finalizer.payload ?? null),
      deps: finalizer.deps ?? [reducer?.id ?? 'reduce'],
      priority: finalizer.priority ?? 0,
      estimatedCostUsd: finalizer.estimatedCostUsd ?? 0,
      cacheTtlMs: finalizer.cacheTtlMs ?? null,
      tags: ['finalize', ...(finalizer.tags ?? [])],
    });
  }
  return normalizeTaskGraph({ graphId, dataClass, nodes, metadata });
}
