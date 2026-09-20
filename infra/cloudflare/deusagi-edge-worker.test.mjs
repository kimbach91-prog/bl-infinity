import assert from 'node:assert/strict';
import { isBlocked, normalizePublicPath, legacyUrlFor, rewritePublicText, validateS0Nonce, computeS0Work } from './deusagi-edge-worker.mjs';

assert.equal(isBlocked('/runtime'), true);
assert.equal(isBlocked('/runtime/federation'), true);
assert.equal(isBlocked('/nodes/windows'), true);
assert.equal(isBlocked('/books/'), false);
assert.equal(isBlocked('/deus/'), false);

assert.equal(normalizePublicPath('/bl-infinity'), '/');
assert.equal(normalizePublicPath('/bl-infinity/books/'), '/books/');
assert.equal(normalizePublicPath('/books/'), '/books/');

const mapped = legacyUrlFor(new URL('https://deusagi.ai/books/?x=1'));
assert.equal(mapped.toString(), 'https://kimbach91-prog.github.io/bl-infinity/books/?x=1');

assert.equal(
  rewritePublicText('x https://kimbach91-prog.github.io/bl-infinity/books/ y'),
  'x https://deusagi.ai/books/ y'
);

assert.equal(validateS0Nonce('DEUS_EDGE_CANARY_V1'), 'DEUS_EDGE_CANARY_V1');
assert.throws(() => validateS0Nonce(''), /BAD_S0_NONCE/);
assert.throws(() => validateS0Nonce('x'.repeat(65)), /BAD_S0_NONCE/);
assert.equal(computeS0Work('DEUS_EDGE_CANARY_V1'), 'f32ebe15');
assert.equal(computeS0Work('DEUS_EDGE_CANARY_V1'), computeS0Work('DEUS_EDGE_CANARY_V1'));
assert.notEqual(computeS0Work('DEUS_EDGE_CANARY_V1'), computeS0Work('DEUS_EDGE_CANARY_V2'));

console.log('DEUSAGI edge unit tests: PASS');
