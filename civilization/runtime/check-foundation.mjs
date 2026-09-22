import { readFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

const readJson = async (relative) => JSON.parse(await readFile(resolve(root, relative), 'utf8'));
const fail = (message) => { throw new Error(message); };

const registry = await readJson('PLATFORM-REGISTRY-v0.1.json');
const schemas = await Promise.all([
  readJson('schemas/provenance-record.schema.json'),
  readJson('schemas/concept-record.schema.json'),
  readJson('schemas/evidence-record.schema.json'),
  readJson('schemas/snapshot-manifest.schema.json')
]);

if (registry.schema !== 'viet-civilization-platform-registry/v0.1') fail('unexpected registry schema');
if (registry.semanticLanguage !== 'VTTN') fail('VTTN must remain the semantic language');
if (registry.transport !== 'DSFP') fail('DSFP must remain the transport profile');

const ids = registry.platforms.map((p) => p.id);
if (new Set(ids).size !== ids.length) fail('platform IDs must be unique');
if (ids.length !== 9) fail('v0.1 must define exactly nine civilization platforms');

for (const schema of schemas) {
  if (schema.$schema !== 'https://json-schema.org/draft/2020-12/schema') fail(`${schema.title}: wrong JSON Schema dialect`);
  if (schema.additionalProperties !== false) fail(`${schema.title}: additionalProperties must fail closed`);
  if (!Array.isArray(schema.required) || schema.required.length === 0) fail(`${schema.title}: required fields missing`);
}

const disclosure = new Set(registry.disclosureClasses);
for (const required of ['PUBLIC','COMMON','RESTRICTED','BLACK_CORE']) {
  if (!disclosure.has(required)) fail(`missing disclosure class ${required}`);
}

const epistemic = new Set(registry.epistemicClasses);
for (const required of ['OBS','INFER','ASSUME','NORM','HYPOTHESIS','UNSOURCED']) {
  if (!epistemic.has(required)) fail(`missing epistemic class ${required}`);
}

const provenance = schemas.find((s) => s.title.startsWith('Việt Văn Minh Provenance'));
for (const field of ['id','platform','epistemicClass','disclosureClass','sources','contentHash']) {
  if (!provenance.required.includes(field)) fail(`provenance must require ${field}`);
}

const snapshot = schemas.find((s) => s.title.startsWith('Sovereign Snapshot'));
if (!snapshot.required.includes('rootHash')) fail('snapshot must require rootHash');

console.log(JSON.stringify({
  ok: true,
  platforms: ids,
  schemas: schemas.map((s) => s.title),
  disclosureClasses: [...disclosure],
  epistemicClasses: [...epistemic]
}, null, 2));
