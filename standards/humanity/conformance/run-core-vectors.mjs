import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateHcsEnvelope } from './validate-envelope.mjs';
import { integrityDigestHcs } from '../runtime/canonicalize-hcs.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const suite = JSON.parse(fs.readFileSync(path.join(here, 'vectors/core-v0.1.json'), 'utf8'));
const options = {
  referenceTime: suite.referenceTime,
  supportedProfiles: new Set(suite.supportedProfiles || []),
  revokedRefs: new Set(suite.revokedRefs || [])
};

let failed = 0;
for (const vector of suite.cases) {
  const result = validateHcsEnvelope(vector.envelope, options);
  const codes = new Set(result.errors.map((e) => e.code));
  const problems = [];

  if (result.valid !== vector.expectedValid) problems.push(`valid=${result.valid}, expected=${vector.expectedValid}`);
  for (const expected of vector.expectedErrors || []) if (!codes.has(expected)) problems.push(`missing error ${expected}`);
  if (vector.expectedDigest) {
    const actual = integrityDigestHcs(vector.envelope);
    if (actual !== vector.expectedDigest) problems.push(`digest=${actual}, expected=${vector.expectedDigest}`);
  }

  if (problems.length) {
    failed += 1;
    console.error(`FAIL ${vector.id}: ${problems.join('; ')}; errors=${[...codes].join(',')}`);
  } else {
    console.log(`PASS ${vector.id}`);
  }
}

if (failed) {
  console.error(`HCS conformance: ${failed}/${suite.cases.length} vectors failed`);
  process.exit(1);
}
console.log(`HCS conformance: ${suite.cases.length}/${suite.cases.length} vectors passed`);
