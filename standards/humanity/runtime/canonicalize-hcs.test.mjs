import test from 'node:test';
import assert from 'node:assert/strict';
import { canonicalizeHcs, sha256Hcs } from './canonicalize-hcs.mjs';

test('object key order does not change canonical bytes', () => {
  const a = { z: 1, a: 'x', nested: { b: 2, a: 1 } };
  const b = { nested: { a: 1, b: 2 }, a: 'x', z: 1 };
  assert.equal(canonicalizeHcs(a), canonicalizeHcs(b));
  assert.equal(sha256Hcs(a), sha256Hcs(b));
});

test('unicode strings and keys normalize to NFC', () => {
  const decomposed = 'e\u0301';
  const composed = 'é';
  assert.equal(canonicalizeHcs({ [decomposed]: decomposed }), canonicalizeHcs({ [composed]: composed }));
});

test('negative zero canonicalizes to zero', () => {
  assert.equal(canonicalizeHcs({ n: -0 }), '{"n":0}');
});

test('non finite numbers fail closed', () => {
  assert.throws(() => canonicalizeHcs({ n: Infinity }), /NON_FINITE/);
  assert.throws(() => canonicalizeHcs({ n: NaN }), /NON_FINITE/);
});

test('undefined fails closed', () => {
  assert.throws(() => canonicalizeHcs({ x: undefined }), /UNDEFINED_FORBIDDEN/);
});

test('post-NFC duplicate keys fail closed', () => {
  const x = {};
  x['e\u0301'] = 1;
  x['é'] = 2;
  assert.throws(() => canonicalizeHcs(x), /DUPLICATE_KEY_AFTER_NFC/);
});
