import assert from 'node:assert/strict';
import { isBlocked, normalizePublicPath, legacyUrlFor, rewritePublicText } from './deusagi-edge-worker.mjs';

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

console.log('DEUSAGI edge unit tests: PASS');
