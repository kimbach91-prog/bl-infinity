import test from 'node:test';
import assert from 'node:assert/strict';
import { installLifeCapabilities, publicLifeSnapshot, wrapHandlersWithLifeEvents } from '../worker/life-worker.mjs';

function fakeDaemon() {
  const events = [];
  return {
    events,
    logger: { warn() {} },
    async emit(event) { events.push(structuredClone(event)); },
    snapshot() {
      return {
        version: 1,
        generation: 42,
        body: { E: 0.6, A: 1 },
        policyWeights: { SECRET_INTERNAL: 0.77 },
        scars: [{ private: 'do-not-project' }],
        leaseOwnerId: 'private-lease-owner',
        lastAction: 'HOLD_STEADY',
        lastEventAt: '2026-09-10T00:00:00.000Z',
        lastMutationAt: null,
        consecutiveQuiet: 3,
        totalEvents: 42,
        totalMutations: 2,
        totalErrors: 1,
      };
    },
  };
}

test('wrapped handler emits sanitized task lifecycle without raw payload or result', async () => {
  const daemon = fakeDaemon();
  const handlers = wrapHandlersWithLifeEvents(new Map([
    ['secret.echo', async (payload) => ({ repeated: payload.secret })],
  ]), daemon);

  const result = await handlers.get('secret.echo')({ secret: 'TOP-SECRET-INPUT' }, { task: { id: 'task-1' } });
  assert.deepEqual(result, { repeated: 'TOP-SECRET-INPUT' });
  assert.deepEqual(daemon.events.map((e) => e.type), ['task-start', 'task-success']);
  assert.equal(JSON.stringify(daemon.events).includes('TOP-SECRET-INPUT'), false);
  assert.equal(daemon.events[0].payload.capability, 'secret.echo');
  assert.equal(daemon.events[0].payload.taskId, 'task-1');
});

test('wrapped handler records only error class and rethrows original error', async () => {
  const daemon = fakeDaemon();
  const handlers = wrapHandlersWithLifeEvents(new Map([
    ['secret.fail', async () => { throw new TypeError('PRIVATE ERROR DETAIL'); }],
  ]), daemon);

  await assert.rejects(() => handlers.get('secret.fail')({ secret: 'DO-NOT-JOURNAL' }, { task: { id: 'task-2' } }), TypeError);
  assert.deepEqual(daemon.events.map((e) => e.type), ['task-start', 'task-error']);
  const serialized = JSON.stringify(daemon.events);
  assert.equal(serialized.includes('DO-NOT-JOURNAL'), false);
  assert.equal(serialized.includes('PRIVATE ERROR DETAIL'), false);
  assert.equal(daemon.events[1].payload.errorClass, 'TypeError');
});

test('public snapshot exposes inspectable state but omits internal policy/scars/lease identity', () => {
  const daemon = fakeDaemon();
  const projected = publicLifeSnapshot(daemon.snapshot());
  assert.equal(projected.generation, 42);
  assert.equal(projected.lastAction, 'HOLD_STEADY');
  assert.deepEqual(projected.body, { E: 0.6, A: 1 });
  const serialized = JSON.stringify(projected);
  assert.equal(serialized.includes('SECRET_INTERNAL'), false);
  assert.equal(serialized.includes('do-not-project'), false);
  assert.equal(serialized.includes('private-lease-owner'), false);
});

test('life.snapshot capability returns the bounded public projection', async () => {
  const daemon = fakeDaemon();
  const handlers = installLifeCapabilities(new Map(), daemon);
  const snapshot = await handlers.get('life.snapshot')();
  assert.equal(snapshot.generation, 42);
  assert.equal(snapshot.totalEvents, 42);
  assert.equal(Object.hasOwn(snapshot, 'policyWeights'), false);
});
