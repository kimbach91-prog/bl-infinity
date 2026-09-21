import test from 'node:test';
import assert from 'node:assert/strict';
import { MemoryLeaseQueue } from '../lib/queue.mjs';
import { TaskGraphBroker } from '../lib/task-graph-broker.mjs';
import {
  FlowContinuitySupervisor,
  continuityRecoveryPlan,
  retryDelayMs,
} from '../lib/flow-continuity.mjs';

class FakeOrchestrator {
  constructor(queue = new MemoryLeaseQueue({ defaultLeaseMs: 50, maxAttempts: 3 })) {
    this.queue = queue;
  }
  async submit(task, options = {}) {
    return this.queue.enqueue(task, options);
  }
}

test('coordinator restart restores succeeded work and does not rerun completed upstream node', async () => {
  const graph = {
    graphId: 'flow',
    runId: 'flow-run-1',
    nodes: [
      { id: 'prep', capability: 'compute.echo' },
      { id: 'final', capability: 'compute.echo', deps: ['prep'] },
    ],
  };
  const queue = new MemoryLeaseQueue();
  const orch = new FakeOrchestrator(queue);
  const first = new TaskGraphBroker(graph);
  await first.materializeReady(orch, { now: 1000 });
  const prep = queue.claim('worker-a', ['compute.echo'], { now: 1001, leaseMs: 100 });
  queue.complete(prep.id, prep.lease.token, { result: { artifact: 'prep-ok' } });

  const restarted = new TaskGraphBroker(graph);
  const supervisor = new FlowContinuitySupervisor({ broker: restarted, orchestrator: orch });
  const recovered = await supervisor.recover({ now: 1010 });
  assert.equal(recovered.snapshot.states.prep.state, 'succeeded');
  assert.deepEqual(recovered.recoveryPlan.keep, ['prep']);
  assert.deepEqual(recovered.snapshot.ready, ['final']);

  const dispatch = await supervisor.dispatchReady({ now: 1011 });
  assert.deepEqual(dispatch.submitted.map((x) => x.nodeId), ['final']);
  assert.equal(queue.list().filter((j) => j.id === 'flow-run-1::prep').length, 1);
});

test('expired lease is fenced: stale worker cannot overwrite recovery worker', () => {
  const queue = new MemoryLeaseQueue({ defaultLeaseMs: 10, maxAttempts: 3 });
  queue.enqueue({ id: 'job', capability: 'compute.echo', payload: null, dataClass: 'public' }, { now: 100 });
  const oldLease = queue.claim('old', ['compute.echo'], { now: 100, leaseMs: 10 });
  queue.sweepExpired(111);
  const newLease = queue.claim('new', ['compute.echo'], { now: 112, leaseMs: 10 });
  assert.notEqual(oldLease.lease.token, newLease.lease.token);
  assert.throws(() => queue.complete('job', oldLease.lease.token, { bad: true }), /invalid lease token/);
  const done = queue.complete('job', newLease.lease.token, { good: true });
  assert.equal(done.state, 'succeeded');
});

test('restore fails closed when persisted task graph fingerprint differs', async () => {
  const queue = new MemoryLeaseQueue();
  const orch = new FakeOrchestrator(queue);
  const original = new TaskGraphBroker({
    graphId: 'g',
    runId: 'r',
    nodes: [{ id: 'a', capability: 'compute.echo', payload: { v: 1 } }],
  });
  await original.materializeReady(orch);
  const changed = new TaskGraphBroker({
    graphId: 'g',
    runId: 'r',
    nodes: [{ id: 'a', capability: 'compute.echo', payload: { v: 2 } }],
  });
  await assert.rejects(() => changed.restoreFromQueue(orch), (error) => error.code === 'FLOW_GRAPH_FINGERPRINT_MISMATCH');
});

test('retry backoff is deterministic, bounded and grows with attempts', () => {
  const seq = [1,2,3,4,5].map((attempt) => retryDelayMs(attempt, {
    baseMs: 1000,
    maxMs: 16000,
    factor: 2,
    jitterRatio: 0,
    key: 'x',
  }));
  assert.deepEqual(seq, [1000,2000,4000,8000,16000]);
  assert.equal(retryDelayMs(3,{baseMs:1000,maxMs:16000,key:'same'}), retryDelayMs(3,{baseMs:1000,maxMs:16000,key:'same'}));
});

test('recovery plan preserves succeeded nodes and stops on deadletter/blocked nodes', () => {
  const plan = continuityRecoveryPlan({
    graphId:'g',runId:'r',
    states:{
      a:{state:'succeeded'},
      b:{state:'submitted'},
      c:{state:'failed'},
      d:{state:'blocked'},
    }
  });
  assert.deepEqual(plan.keep,['a']);
  assert.deepEqual(plan.resume,['b']);
  assert.deepEqual(plan.stop,['c','d']);
  assert.equal(plan.canContinue,false);
});
