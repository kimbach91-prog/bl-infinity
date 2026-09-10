import assert from 'node:assert/strict';
import { scoreJob } from './governor.mjs';
import { normalizeCarbonSignal } from './adapters/carbon-aware.mjs';
import { simulateOpenAdREvent } from './adapters/openadr-sim.mjs';
import { chooseWindow } from './adapters/workload-scheduler.mjs';

const carbon = normalizeCarbonSignal({ carbonIntensity: 200, minIntensity: 100, maxIntensity: 500, source: 'fixture' });
assert.equal(carbon.carbon_intensity_norm, 0.25);

const job = { job_id: 'J1', authority: true, runtime_verified: true, deadline_feasible: true, risk_score: 0.1, urgency: 0.4 };
const d1 = scoreJob(job, { carbon_intensity_norm: 0.25, energy_price_norm: 0.4, runtime_reliability: 0.9 });
assert.equal(d1.eligible, true);
assert.equal(d1.action, 'CANDIDATE_DISPATCH');

const denied = scoreJob({ ...job, authority: false }, { carbon_intensity_norm: 0.1, energy_price_norm: 0.1, runtime_reliability: 1 });
assert.equal(denied.eligible, false);
assert.equal(denied.action, 'HOLD');

const drNoAuth = simulateOpenAdREvent({ event_id: 'E1', requested_kw: 50 }, { available_kw: 80, max_curtail_kw: 30, authority: false });
assert.equal(drNoAuth.simulated_curtail_kw, 0);
assert.equal(drNoAuth.external_dispatch, false);

const drAuth = simulateOpenAdREvent({ event_id: 'E2', requested_kw: 50 }, { available_kw: 80, max_curtail_kw: 30, authority: true });
assert.equal(drAuth.simulated_curtail_kw, 30);

const windows = [
  { carbon_intensity_norm: 0.8, energy_price_norm: 0.7, runtime_reliability: 0.99 },
  { carbon_intensity_norm: 0.2, energy_price_norm: 0.3, runtime_reliability: 0.95 },
];
const choice = chooseWindow(job, windows, scoreJob);
assert.equal(choice.action, 'CANDIDATE_DISPATCH');
assert.equal(choice.selected.window, windows[1]);
assert.equal(choice.external_execution_performed, false);

console.log(JSON.stringify({ status: 'PASS', tests: 10, selected_utility: choice.selected.decision.utility }));
