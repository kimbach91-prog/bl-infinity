import { writeFile } from 'node:fs/promises';
import { makeSummon, summonPrompt } from './summon.js';
import { writeSummon } from './storage.js';
import { asTransitSeat, makeTransitBundle, transitPrompt } from './transit.js';

async function main() {
  const task = process.argv.slice(2).join(' ').trim() || process.env.DEUS_TASK?.trim();
  if (!task) {
    throw new Error('Usage: npm run transit -- "task"');
  }

  const configuredSeats = process.env.BL_TRANSIT_SEATS?.trim() || 'CLAUDE,GEMINI,GROK';
  const targets = configuredSeats
    .split(',')
    .map((value) => asTransitSeat(value.trim().toUpperCase()))
    .filter((value, index, all) => all.indexOf(value) === index);

  if (!targets.length) {
    throw new Error('BL_TRANSIT_SEATS resolved to no supported targets');
  }

  const callId = `call_${crypto.randomUUID()}`;
  console.log(`DEUS multi-core transit call_id=${callId}`);

  for (const target of targets) {
    const packet = makeSummon({
      target,
      task,
      callId,
      phase: 'DIRECT',
      metadata: {
        mode: 'DEUS_MULTICORE_TRANSIT',
        logical_route: `BL://DEUS/BRIDGE/${target}`,
        transport: 'INTERACTIVE_SESSION_ZERO_API',
        transit_state: 'PREPARED'
      }
    });

    const packetPath = await writeSummon(packet);
    const genericPromptPath = `${packetPath}.prompt.txt`;
    await writeFile(genericPromptPath, summonPrompt(packet), 'utf8');

    const transit = makeTransitBundle(packet);
    const transitPath = `${packetPath}.transit.json`;
    const transitPromptPath = `${packetPath}.transit.prompt.txt`;
    await writeFile(transitPath, JSON.stringify(transit, null, 2), 'utf8');
    await writeFile(transitPromptPath, transitPrompt(transit), 'utf8');

    console.log(`${target}: summon=${packetPath}`);
    console.log(`${target}: transit=${transitPath}`);
    console.log(`${target}: prompt=${transitPromptPath}`);
  }

  console.log('state=PREPARED');
  console.log('Reality veto: PREPARED is not SUBMITTED, ACK_ACCEPTED, RETURN_INGESTED, or COMMITTED.');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
