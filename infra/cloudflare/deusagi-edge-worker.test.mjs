import assert from 'node:assert/strict';
import {
  isBlocked,
  normalizePublicPath,
  legacyUrlFor,
  rewritePublicText,
  validateS0Nonce,
  computeS0Work,
  decodeAeadKeyB64,
  validateSinkUrl,
  makeScheduledPayload,
  encryptScheduledPayload
} from './deusagi-edge-worker.mjs';

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

assert.equal(validateSinkUrl('https://example.com/heartbeat'), 'https://example.com/heartbeat');
assert.equal(validateSinkUrl(''), null);
assert.throws(() => validateSinkUrl('http://example.com/heartbeat'), /SINK_MUST_USE_HTTPS/);
assert.throws(() => validateSinkUrl('https://u:p@example.com/heartbeat'), /SINK_CREDENTIALS_IN_URL_FORBIDDEN/);

const keyB64 = Buffer.from('0123456789abcdef0123456789abcdef', 'utf8').toString('base64');
assert.equal(decodeAeadKeyB64(keyB64).length, 32);
assert.equal(decodeAeadKeyB64(''), null);
assert.throws(() => decodeAeadKeyB64(Buffer.from('short').toString('base64')), /BAD_AEAD_KEY_LENGTH/);

const scheduled = makeScheduledPayload({
  scheduledTime: Date.UTC(2026, 8, 20, 11, 37, 0),
  cron: '7,37 * * * *'
});
assert.equal(scheduled.schema, 'deus-cloudflare-daemon-heartbeat/1');
assert.equal(scheduled.executor, 'CLOUDFLARE_WORKERS');
assert.equal(scheduled.data_class, 'S0_PUBLIC');
assert.equal(scheduled.canonical_write, false);

const envelope = await encryptScheduledPayload(scheduled, keyB64);
assert.equal(envelope.schema, 'deus-cloudflare-daemon-envelope/1');
assert.equal(envelope.alg, 'A256GCM');
assert.equal(envelope.data_class_hint, 'S0_PUBLIC');
assert.ok(envelope.iv_b64.length > 8);
assert.ok(envelope.ciphertext_and_tag_b64.length > 32);

console.log('DEUSAGI edge unit tests: PASS');
