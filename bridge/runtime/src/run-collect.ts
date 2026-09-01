import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { listReturns, paths } from './storage.js';
import type { ReturnPacket } from './types.js';

async function main() {
  const [callId] = process.argv.slice(2);
  if (!callId) throw new Error('Usage: npm run collect -- <call_id>');
  const files = await listReturns(callId);
  const returns: ReturnPacket[] = [];
  for (const file of files) {
    returns.push(JSON.parse(await readFile(file, 'utf8')) as ReturnPacket);
  }
  const bundle = {
    protocol: 'BL-SUMMON/1.0',
    packet_type: 'RETURN_BUNDLE',
    call_id: callId,
    collected_at: new Date().toISOString(),
    count: returns.length,
    returns
  };
  const out = join(paths.archive(), `${callId}__return-bundle.json`);
  await writeFile(out, JSON.stringify(bundle, null, 2), 'utf8');
  console.log(`returns=${returns.length}`);
  console.log(`bundle=${out}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
