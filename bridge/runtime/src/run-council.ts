import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { makeSummon, summonPrompt } from './summon.js';
import { writeSummon } from './storage.js';

async function main() {
  const agenda = process.argv.slice(2).join(' ').trim() || process.env.BL_AGENDA?.trim();
  if (!agenda) throw new Error('Usage: npm run council:open -- "agenda"');
  const seats = (process.env.BL_COUNCIL_SEATS || 'GPT,CLAUDE,GEMINI,GROK')
    .split(',')
    .map((x) => x.trim().toUpperCase())
    .filter(Boolean);
  const callId = `council_${crypto.randomUUID()}`;

  for (const target of seats) {
    const packet = makeSummon({
      target,
      task: `AGENDA:\n${agenda}\n\nProduce an independent blind proposal before seeing any other seat's answer. Include thesis, assumptions, causal structure, evidence needed, falsifiers, and smallest useful next experiment/action.`,
      callId,
      phase: 'BLIND_PROPOSAL',
      metadata: { agenda }
    });
    const packetPath = await writeSummon(packet);
    await writeFile(resolve(`${packetPath}.prompt.txt`), summonPrompt(packet), 'utf8');
    console.log(`${target}: ${packetPath}`);
  }
  console.log(`call_id=${callId}`);
  console.log('After each seat answers in its normal chat/session, save the answer to a text file and ingest with npm run return. Then use npm run collect -- <call_id>.');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
