import fs from 'node:fs';

const registry = JSON.parse(fs.readFileSync(new URL('../HCS-REGISTRY-v0.1.json', import.meta.url), 'utf8'));
const schema = JSON.parse(fs.readFileSync(new URL('../schemas/hcs-envelope.schema.json', import.meta.url), 'utf8'));

const ids = new Set(registry.standards.map((x) => x.id));
if (ids.size !== registry.standards.length) throw new Error('duplicate HCS standard id');
for (const required of ['HCS-01','HCS-02','HCS-03','HCS-04','HCS-05','HCS-06','HCS-07','HCS-08','HCS-09','HCS-10']) {
  if (!ids.has(required)) throw new Error(`missing ${required}`);
}
for (const [profile, members] of Object.entries(registry.profiles)) {
  if (!members.length) throw new Error(`empty profile ${profile}`);
  for (const id of members) if (!ids.has(id)) throw new Error(`${profile} references unknown ${id}`);
}
for (const cls of ['OBSERVED','REPORTED','INFERRED','ASSUMED','PREDICTED','UNKNOWN','DISPUTED']) {
  if (!registry.epistemicClasses.includes(cls)) throw new Error(`missing epistemic class ${cls}`);
}
for (const st of ['PROPOSED','AUTHORIZED','ATTEMPTED','OBSERVED_COMPLETE','INFERRED_OUTCOME','FAILED','REVOKED']) {
  if (!registry.actionStates.includes(st)) throw new Error(`missing action state ${st}`);
}
if (schema.properties?.action?.properties?.state?.enum?.join('|') !== registry.actionStates.join('|')) {
  throw new Error('schema action states drift from registry');
}
if (schema.properties?.epistemic?.properties?.class?.enum?.join('|') !== registry.epistemicClasses.join('|')) {
  throw new Error('schema epistemic classes drift from registry');
}
if (!schema.required?.includes('authority') || !schema.required?.includes('provenance') || !schema.required?.includes('integrity')) {
  throw new Error('HCS envelope missing mandatory authority/provenance/integrity');
}
console.log('HCS foundation integrity OK');
