# Instruction fabric: scoped integration

This module adds instruction atoms to the existing Federation runtime, Participation Registry, Compute Accord, Logical Resource Compiler and TaskGraphBroker. It does not replace those components or grant authority to Atlas data.

## Installation contract

Use an authorized host-created binding, a pinned local operator module, an explicit input contract, a verifier, and a frozen canary. The caller must supply authority scope, expiry and zero-spend entitlement. These fields are not an authentication protocol; untrusted clients or source records must never be permitted to construct bindings.

The shipped driver is a local Node worker-thread driver. It is suitable for trusted pure operators, not hostile code. A hash pin covers the entry module; deployment must separately pin its dependency closure. Unknown remote stop state remains a capacity hold. There is no generic shell, provider signup, credential handling, or arbitrary endpoint probing.

Integrate through the existing runtime API:

```js
const atomStore = new AtomStore(authorizedSharedResourceDbPath);
const atoms = new InstructionFabric({
  store: atomStore,
  operators: hostInstalledOperatorContracts,
  bindings: hostAuthorizedBindings,
});
const state = createSqliteFederationState(taskScopedQueueDbPath);
const runtime = createFederationRuntime({
  providers: hostAuthorizedBindings.map(b => atoms.provider(b.routeId)),
  state,
});
runtime.executor.adapters.set('instruction-atom', atoms.adapter());
const result = await executeAtomGraph({ runtime, fabric: atoms, graph, maxParallel: 2 });
```

Use an isolated task queue containing only the graph's atom work for this convenience runner. It invokes the existing queue consumer and is not a filter for an unrelated global queue. The ordinary scheduler may instead use the adapter directly with its existing scoped queue. Resource aliases sharing hardware must share the same pool identity and AtomStore database. Separate databases are not distributed resource consensus.

`PROBE`, `LEASE`, `RUN`, `CHECKPOINT`, `RESULT`, `CANCEL` and `RELEASE` are host-facing verbs. The actual worker receives only a bound input and the selected operator. Expiry is not stop proof. A lost executor cannot be credited as released merely because its TTL elapsed. Recover an orphan reservation only with authorized evidence of actual termination; this integration intentionally does not offer a force-release bypass.

## Dataflow and reuse

`compileAtomTree` creates a bounded hot DAG from concrete leaf partitions, under an addressable logical descriptor up to 1T. It does not enumerate 1T workers or create physical capacity. The inherited LRC performs placement planning; actual dispatch still requires current authorization, a fresh canary and a resource lease.

Cache keys include normalized input, program, verifier, environment, input validation, binding, tenant and data class. Cache reuse validates retained bytes and receipt concordance; new input recomputes only the dependency cone. It does not rerun the expensive verifier on every identical result. Do not use the legacy generic cache for atom tasks. Revocation and input validation also apply to cached and queue-restored results.

Typed reducers cover verified deterministic outputs, evaluated optimization candidates, sufficient-statistic simulation summaries and evidence-preserving reasoning claims. The reasoning reducer records disagreement; it does not establish truth by voting or replace a domain evaluator.

## Verification

Run the dependency-free suite with the repository's tested Node 22.16.0 runtime:

```sh
cd runtime/federation
node --test --test-concurrency=1 test/instruction-fabric.test.mjs test/compute-accord-gate.test.mjs test/durable.test.mjs test/task-graph-broker.test.mjs test/logical-resource-compiler.test.mjs test/universal-participation-registry.test.mjs
node scripts/verify-instruction-fabric.mjs --out /absolute/new-empty-evidence-directory
```

For real data, supply `--input` with a source-verified JSON array of public Atlas rows. Use a new output directory for an independent run; existing receipts retain their original host binding/authorization identity. The verifier creates three matched cold/reuse rounds, durable reopen checks and a clearly marked controlled-delta fixture without modifying the source snapshot.

Workflow run 36086275447 verified 87 tests in each of two allocated CI jobs, split a digest-bound 124,397-row public Atlas snapshot into 62,199 and 62,198 rows, and joined their receipts with an actual leased final reducer. Its final public artifact is 10843514604, SHA256 c0e55d1813c1960ff241abb2d7490ca01af1de2f4d719a48cd327194556f3958. These are independent job allocations within one provider, not proof of different physical machines or cross-provider consensus.

The local full-snapshot replay created 16 shards and 21 DAG nodes, with two worker threads on one host. Changing one leaf required three executions while retaining 18 results. Cold graph execution can be slower than a single serial pass because lifecycle, verification and durable coordination have overhead. Reuse ratios compare the same graph with retained verified state, not hardware acceleration or universal speedup. Report first-pass cost as well as reuse benefit.

## Activation boundaries

Importing this module or merging its tests does not install it on every existing node. Production hosts must explicitly bind the adapter under their current deployment policy, attest the exact artifact, run compatibility checks and return an adoption receipt. Historical GPU/SIMD/kernel benchmarks are not erased by a CPU-only integration test, and are not evidence that a GPU was allocated for this test. Private kernel modules remain outside this public repository.

Public APIs, market listings, CIDRs, certificate names and cloud prefixes remain data unless a separate legitimate execution interface and current task authorization exist. No new paid resources, arbitrary third-party probes or changes to deployment protection are part of this integration.
