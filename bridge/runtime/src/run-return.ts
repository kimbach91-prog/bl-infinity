import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { readJson, writeReturn } from './storage.js';
import { newId, type ReturnPacket, type SummonPacket } from './types.js';

async function main() {
  const [summonPathArg, actorArg, responsePathArg] = process.argv.slice(2);
  if (!summonPathArg || !actorArg || !responsePathArg) {
    throw new Error('Usage: npm run return -- <summon.json> <GPT|CLAUDE|GEMINI|GROK> <response.txt>');
  }

  const summon = await readJson<SummonPacket>(summonPathArg);
  const actor = actorArg.trim().toUpperCase();
  if (String(summon.target).toUpperCase() !== actor) {
    throw new Error(`Return actor ${actor} does not match summon target ${summon.target}`);
  }

  const content = await readFile(resolve(responsePathArg), 'utf8');
  const packet: ReturnPacket = {
    protocol: 'BL-SUMMON/1.0',
    packet_type: 'RETURN',
    return_id: newId('return'),
    summon_id: summon.summon_id,
    call_id: summon.call_id,
    created_at: new Date().toISOString(),
    actor,
    content: content.trim(),
    evidence_refs: [],
    parent_refs: [summon.summon_id],
    lineage: summon.lineage ?? null,
    status: 'COMPLETE',
    metadata: { source_response_path: resolve(responsePathArg) }
  };

  const path = await writeReturn(packet);
  console.log(`return=${path}`);
  console.log(`call_id=${packet.call_id}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
