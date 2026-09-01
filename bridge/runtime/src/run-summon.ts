import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { makeSummon, summonPrompt } from './summon.js';
import { writeSummon } from './storage.js';

async function main() {
  const [targetArg, ...taskParts] = process.argv.slice(2);
  const task = taskParts.join(' ').trim() || process.env.DEUS_TASK?.trim();
  if (!targetArg || !task) {
    throw new Error('Usage: npm run summon -- GPT "task"  (targets may be comma-separated)');
  }

  const targets = targetArg.split(',').map((x) => x.trim().toUpperCase()).filter(Boolean);
  const callId = `call_${crypto.randomUUID()}`;
  for (const target of targets) {
    const packet = makeSummon({ target, task, callId, phase: 'DIRECT' });
    const packetPath = await writeSummon(packet);
    const promptPath = resolve(`${packetPath}.prompt.txt`);
    await writeFile(promptPath, summonPrompt(packet), 'utf8');
    console.log(`${target}: ${packetPath}`);
    console.log(`${target} prompt: ${promptPath}`);
  }
  console.log(`call_id=${callId}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
