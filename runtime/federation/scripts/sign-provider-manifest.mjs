import { readFile, writeFile } from 'node:fs/promises';
import { signProviderManifest } from '../lib/manifest.mjs';

const [input, privateKeyPath, keyId, output] = process.argv.slice(2);
if (!input || !privateKeyPath || !keyId || !output) {
  console.error('usage: node scripts/sign-provider-manifest.mjs <manifest.json> <private.pem> <key-id> <signed.json>');
  process.exit(2);
}
const manifest = JSON.parse(await readFile(input, 'utf8'));
const privatePem = await readFile(privateKeyPath, 'utf8');
const signed = signProviderManifest(manifest, privatePem, keyId);
await writeFile(output, `${JSON.stringify(signed, null, 2)}\n`, { flag: 'wx' });
console.log(`Wrote signed manifest to ${output}`);
