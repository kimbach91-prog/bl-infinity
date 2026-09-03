import { generateKeyPairSync } from 'node:crypto';
import { writeFile } from 'node:fs/promises';

const prefix = process.argv[2] || 'provider';
const { publicKey, privateKey } = generateKeyPairSync('ed25519');
const publicPem = publicKey.export({ type: 'spki', format: 'pem' });
const privatePem = privateKey.export({ type: 'pkcs8', format: 'pem' });
await writeFile(`${prefix}.public.pem`, publicPem, { mode: 0o644, flag: 'wx' });
await writeFile(`${prefix}.private.pem`, privatePem, { mode: 0o600, flag: 'wx' });
console.log(`Created ${prefix}.public.pem and ${prefix}.private.pem. Keep the private key secret and never commit it.`);
