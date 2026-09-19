import test from 'node:test';
import assert from 'node:assert/strict';
import {
  canonicalizeHcs,
  sha256Hcs,
  integrityTargetHcs,
  integrityDigestHcs,
  verifyIntegrityDigestHcs,
  HCS_CANONICALIZATION_PROFILE,
  HCS_INTEGRITY_TARGET_PROFILE
} from './canonicalize-hcs.mjs';

test('declares RFC 8785 and detached integrity profiles', () => {
  assert.equal(HCS_CANONICALIZATION_PROFILE, 'urn:hcs:canonicalization:rfc8785-jcs');
  assert.equal(HCS_INTEGRITY_TARGET_PROFILE, 'urn:hcs:integrity-target:envelope-without-integrity-v1');
});

test('object key order does not change canonical bytes', () => {
  const a = { z: 1, a: 'x', nested: { b: 2, a: 1 } };
  const b = { nested: { a: 1, b: 2 }, a: 'x', z: 1 };
  assert.equal(canonicalizeHcs(a), canonicalizeHcs(b));
  assert.equal(sha256Hcs(a), sha256Hcs(b));
});

test('RFC 8785 preserves Unicode string data rather than normalizing it', () => {
  const decomposed = 'e\u0301';
  const composed = 'é';
  assert.notEqual(canonicalizeHcs({ value: decomposed }), canonicalizeHcs({ value: composed }));
});

test('negative zero serializes to zero under ECMAScript/JCS rules', () => {
  assert.equal(canonicalizeHcs({ n: -0 }), '{"n":0}');
});

test('non finite numbers fail closed', () => {
  assert.throws(() => canonicalizeHcs({ n: Infinity }), /NON_FINITE/);
  assert.throws(() => canonicalizeHcs({ n: NaN }), /NON_FINITE/);
});

test('undefined and bigint fail closed', () => {
  assert.throws(() => canonicalizeHcs({ x: undefined }), /UNDEFINED_FORBIDDEN/);
  assert.throws(() => canonicalizeHcs({ x: 1n }), /BIGINT_FORBIDDEN/);
});

test('lone UTF-16 surrogates fail closed', () => {
  assert.throws(() => canonicalizeHcs({ x: '\ud800' }), /INVALID_UNICODE/);
  assert.throws(() => canonicalizeHcs({ '\udc00': 1 }), /INVALID_UNICODE/);
});

test('RFC 8785 sample-compatible ordering and number serialization', () => {
  const sample = {
    literals: [null, true, false],
    numbers: [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
    string: "€$\u000f\nA'B\"\\\\\"/"
  };
  const out = canonicalizeHcs(sample);
  assert.ok(out.startsWith('{"literals":[null,true,false],"numbers":['));
  assert.ok(out.includes('333333333.3333333'));
  assert.ok(out.includes('1e+30'));
  assert.ok(out.includes('0.002'));
});

test('integrity target excludes only top-level integrity', () => {
  const envelope = {
    hcsVersion: '0.1',
    payload: { integrity: 'payload-field-must-remain' },
    integrity: { digestValue: 'placeholder' }
  };
  assert.deepEqual(integrityTargetHcs(envelope), {
    hcsVersion: '0.1',
    payload: { integrity: 'payload-field-must-remain' }
  });
});

test('detached digest is independent of integrity carrier but binds content', () => {
  const envelope = {
    hcsVersion: '0.1',
    messageId: 'message-0001',
    payload: { value: 1 },
    integrity: { digestValue: '' }
  };
  const digest = integrityDigestHcs(envelope);
  envelope.integrity.digestValue = digest;
  assert.equal(verifyIntegrityDigestHcs(envelope), true);
  envelope.integrity.proofRef = 'urn:proof:changed-carrier';
  assert.equal(verifyIntegrityDigestHcs(envelope), true);
  envelope.payload.value = 2;
  assert.equal(verifyIntegrityDigestHcs(envelope), false);
});
