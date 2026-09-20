import test from 'node:test';
import assert from 'node:assert/strict';
import { planTransportRoute, publicProviderRegistry } from '../src/provider-registry.mjs';

test('zero-model fast path needs no provider inference', () => {
  const plan = planTransportRoute({ requires_inference: false, data_class: 'S0' });
  assert.equal(plan.state, 'READY');
  assert.equal(plan.code, 'ZERO_MODEL_FAST_PATH');
  assert.equal(plan.model_usage, false);
  assert.equal(plan.provider_inference_cost, 0);
});

test('free inference is never promised for OpenAI', () => {
  const [openai] = publicProviderRegistry();
  assert.equal(openai.provider_id, 'openai');
  assert.equal(openai.billing.free_inference_guaranteed, false);
  assert.equal(openai.billing.chatgpt_subscription_includes_api_usage, false);
});

test('OpenAI intelligence route holds until runtime canary exists', () => {
  const plan = planTransportRoute({ requires_inference: true, preferred_provider: 'openai', data_class: 'S0' });
  assert.equal(plan.state, 'HOLD');
  assert.equal(plan.code, 'OPENAI_ROUTE_NOT_RUNTIME_VERIFIED');
  assert.equal(plan.free_inference_guaranteed, false);
});

test('sealed data never falls back to free/fast external route', () => {
  const plan = planTransportRoute({ requires_inference: false, data_class: 'S2' });
  assert.equal(plan.state, 'HOLD');
  assert.equal(plan.code, 'SEALED_ROUTE_REQUIRED');
});

test('unknown provider does not silently substitute OpenAI', () => {
  const plan = planTransportRoute({ requires_inference: true, preferred_provider: 'other-ai', data_class: 'S0' });
  assert.equal(plan.state, 'HOLD');
  assert.equal(plan.code, 'PROVIDER_NOT_REGISTERED_IN_V0_1');
});
