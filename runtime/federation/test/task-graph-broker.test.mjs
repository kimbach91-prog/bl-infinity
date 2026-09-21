import test from 'node:test';
import assert from 'node:assert/strict';
import { MemoryLeaseQueue } from '../lib/queue.mjs';
import {
  normalizeTaskGraph,
  TaskGraphBroker,
  compileScatterReduceGraph,
} from '../lib/task-graph-broker.mjs';

class FakeOrchestrator {
  constructor() { this.queue = new MemoryLeaseQueue(); this.submitted = []; }
  async submit(task, options = {}) {
    this.submitted.push({ task, options });
    return this.queue.enqueue(task, options);
  }
}

function complete(orchestrator, taskId, result, now = Date.now()) {
  const claim = orchestrator.queue.claim('worker', ['compute.echo', 'reduce.pick', 'final.render'], { now, leaseMs: 1000 });
  assert.equal(claim.id, taskId);
  orchestrator.queue.complete(taskId, claim.lease.token, { result });
}

test('validates DAG and rejects cycles', () => {
  const graph = normalizeTaskGraph({
    graphId: 'g1',
    nodes: [
      { id: 'a', capability: 'compute.echo' },
      { id: 'b', capability: 'compute.echo', deps: ['a'] },
    ],
  });
  assert.deepEqual(graph.order, ['a', 'b']);
  assert.throws(() => normalizeTaskGraph({
    graphId: 'bad',
    nodes: [
      { id: 'a', capability: 'compute.echo', deps: ['b'] },
      { id: 'b', capability: 'compute.echo', deps: ['a'] },
    ],
  }), /cycle/);
});

test('materializes independent roots together and unlocks reducer only after all roots succeed', async () => {
  const orchestrator = new FakeOrchestrator();
  const broker = new TaskGraphBroker({
    graphId: 'render-search',
    nodes: [
      { id: 'c1', capability: 'compute.echo', payload: { p: 1 } },
      { id: 'c2', capability: 'compute.echo', payload: { p: 2 } },
      { id: 'reduce', capability: 'reduce.pick', deps: ['c1', 'c2'] },
    ],
  });

  const roots = await broker.materializeReady(orchestrator);
  assert.deepEqual(roots.map((x) => x.nodeId), ['c1', 'c2']);
  assert.equal(broker.snapshot().counts.submitted, 2);
  assert.deepEqual(broker.snapshot().ready, []);

  const t0=Date.now()+10;
  complete(orchestrator, 'render-search::c1', { score: 1 }, t0);
  await broker.refresh(orchestrator, { now: t0+10 });
  assert.equal(broker.snapshot().counts.succeeded, 1);
  assert.deepEqual(broker.snapshot().ready, []);

  complete(orchestrator, 'render-search::c2', { score: 2 }, t0+20);
  const advanced = await broker.advance(orchestrator, { now: t0+30 });
  assert.deepEqual(advanced.submitted.map((x) => x.nodeId), ['reduce']);
  const reducerTask = orchestrator.submitted.at(-1).task;
  assert.deepEqual(reducerTask.payload.upstream.c1, { score: 1 });
  assert.deepEqual(reducerTask.payload.upstream.c2, { score: 2 });
});

test('fail-closed graph blocks downstream nodes after deadletter', async () => {
  const orchestrator = new FakeOrchestrator();
  const broker = new TaskGraphBroker({
    graphId: 'g2',
    nodes: [
      { id: 'a', capability: 'compute.echo' },
      { id: 'b', capability: 'compute.echo', deps: ['a'] },
    ],
  });
  await broker.materializeReady(orchestrator);
  const now=Date.now()+10;
  const claim = orchestrator.queue.claim('worker', ['compute.echo'], { now, leaseMs: 100 });
  orchestrator.queue.fail(claim.id, claim.lease.token, new Error('boom'), { terminal: true, now: now+1 });
  await broker.refresh(orchestrator, { now: now+2 });
  const snap = broker.snapshot();
  assert.equal(snap.states.a.state, 'failed');
  assert.equal(snap.states.b.state, 'blocked');
  assert.equal(snap.verdict, 'FAILED');
});

test('scatter-reduce compiler emits a stable bounded graph instead of materializing logical cell cardinality', () => {
  const graph = compileScatterReduceGraph({
    graphId: 'dige-c33',
    scatter: Array.from({ length: 7 }, (_, i) => ({
      id: `candidate-${i + 1}`,
      capability: 'compute.echo',
      payload: { threshold: 0.014 + i * 0.002 },
      virtualWorkUnits: '1000000000000',
    })),
    reducer: { id: 'visual-gate', capability: 'reduce.pick' },
    finalizer: { id: 'final-render', capability: 'final.render' },
    metadata: { logicalHypothesisSpace: '1T' },
  });
  assert.equal(graph.nodes.length, 9);
  assert.equal(graph.nodes.filter((n) => n.tags.includes('scatter')).length, 7);
  assert.deepEqual([...graph.nodes.find((n) => n.id === 'visual-gate').deps].sort(), Array.from({ length: 7 }, (_, i) => `candidate-${i + 1}`));
  assert.equal(graph.fingerprint.length, 64);
});

test('task idempotency changes when dependency results change', async () => {
  const orchestrator = new FakeOrchestrator();
  const broker = new TaskGraphBroker({
    graphId: 'digest-test',
    nodes: [
      { id: 'a', capability: 'compute.echo' },
      { id: 'b', capability: 'reduce.pick', deps: ['a'] },
    ],
  });
  await broker.materializeReady(orchestrator);
  const now2=Date.now()+10;
  complete(orchestrator, 'digest-test::a', { x: 1 }, now2);
  await broker.refresh(orchestrator, { now: now2+10 });
  const first = broker.buildTask('b').idempotencyKey;

  const broker2 = new TaskGraphBroker({
    graphId: 'digest-test',
    nodes: [
      { id: 'a', capability: 'compute.echo' },
      { id: 'b', capability: 'reduce.pick', deps: ['a'] },
    ],
  });
  broker2.state.get('a').state = 'succeeded';
  broker2.state.get('a').result = { x: 2 };
  broker2.state.get('a').resultDigest = 'different';
  const second = broker2.buildTask('b').idempotencyKey;
  assert.notEqual(first, second);
});
