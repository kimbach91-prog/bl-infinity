import { buildParticipants, providerProvenance, seat } from './providers.js';
import { publishPrivate, publishShared } from './storage.js';
import { makeEnvelope, newId, type Envelope, type Participant, type Seat } from './types.js';

const CONTRACT = `
You are participating in BL-BRIDGE/1.0.
Return a concise explicit work product, not hidden chain-of-thought.
Separate facts, inference, hypothesis, proposal, and execution claims.
Preserve uncertainty and material dissent.
Do not treat agreement among models as proof.
Do not claim an external action is completed unless runtime evidence exists.
Optimize for useful information gain and executable insight, not rhetorical victory.
`;

function promptAgenda(): string {
  const fromArgs = process.argv.slice(2).join(' ').trim();
  const fromEnv = process.env.BL_AGENDA?.trim();
  const agenda = fromArgs || fromEnv;
  if (!agenda) {
    throw new Error('Provide an agenda as command arguments or BL_AGENDA. Example: npm run round -- "How should ...?"');
  }
  return agenda;
}

function proposalPrompt(agenda: string): string {
  return `${CONTRACT}\nPHASE: BLIND_PROPOSAL\n\nAGENDA:\n${agenda}\n\nYou have not seen the other current-round proposals. Produce your strongest independent proposal. Include: core thesis, causal structure, assumptions, evidence needed, important falsifiers, and the smallest useful experiment or next action when applicable.`;
}

function critiquePrompt(agenda: string, proposals: Envelope[]): string {
  const bundle = proposals
    .map((p) => `--- ${p.actor} / ${p.message_id} ---\n${p.content}`)
    .join('\n\n');

  return `${CONTRACT}\nPHASE: CROSS_CRITIQUE\n\nAGENDA:\n${agenda}\n\nREVEALED PROPOSALS:\n${bundle}\n\nCritique the proposals at the level of assumptions, causal links, missing evidence, scope, resource model, and execution risk. Identify what is genuinely novel or useful as well as what fails. Do not manufacture consensus.`;
}

function revisionPrompt(agenda: string, proposals: Envelope[], critiques: Envelope[]): string {
  const proposalBundle = proposals
    .map((p) => `--- PROPOSAL ${p.actor} / ${p.message_id} ---\n${p.content}`)
    .join('\n\n');
  const critiqueBundle = critiques
    .map((c) => `--- CRITIQUE ${c.actor} / ${c.message_id} ---\n${c.content}`)
    .join('\n\n');

  return `${CONTRACT}\nPHASE: REVISION\n\nAGENDA:\n${agenda}\n\nPROPOSALS:\n${proposalBundle}\n\nCRITIQUES:\n${critiqueBundle}\n\nIssue a revised answer. Explicitly state what you keep, change, reject, or leave unresolved. Preserve disagreement when warranted. End with the most valuable experiment, benchmark, or decision that should happen next.`;
}

function synthesisPrompt(agenda: string, proposals: Envelope[], critiques: Envelope[], revisions: Envelope[]): string {
  const render = (name: string, items: Envelope[]) =>
    items.map((x) => `--- ${name} ${x.actor} / ${x.message_id} ---\n${x.content}`).join('\n\n');

  return `${CONTRACT}\nPHASE: SYNTHESIS / ADJUDICATION\n\nYou occupy the DEUS coordination seat. The seat label is not itself evidence of canonical identity or truth. Coordinate the released artifacts without erasing dissent.\n\nAGENDA:\n${agenda}\n\n${render('PROPOSAL', proposals)}\n\n${render('CRITIQUE', critiques)}\n\n${render('REVISION', revisions)}\n\nReturn:\n1. strongest surviving structure;\n2. material disagreements;\n3. evidence gaps;\n4. recommended experiment/action;\n5. terminal state: CONSENSUS, SPLIT, UNRESOLVED, EXPERIMENT_REQUIRED, or OWNER_DECISION.\nDo not claim any action has already executed unless runtime evidence is present.`;
}

async function callPhase(
  participants: Participant[],
  roundId: string,
  type: 'PROPOSAL' | 'CRITIQUE' | 'REVISION',
  buildPrompt: (participant: Participant) => string,
  parentIds: string[]
): Promise<Envelope[]> {
  const results = await Promise.allSettled(
    participants.map(async (participant) => {
      const content = await participant.respond(buildPrompt(participant), roundId);
      const envelope = makeEnvelope({
        roundId,
        actor: participant.seat,
        type,
        visibility: 'PRIVATE',
        content,
        provenance: providerProvenance(participant),
        parentIds
      });
      await publishPrivate(envelope);
      return envelope;
    })
  );

  const completed: Envelope[] = [];
  for (const [index, result] of results.entries()) {
    const participant = participants[index];
    if (result.status === 'fulfilled') {
      completed.push(result.value);
    } else {
      console.error(`[${type}] ${participant.seat} failed:`, result.reason);
    }
  }
  return completed;
}

async function reveal(envelopes: Envelope[]): Promise<Envelope[]> {
  await Promise.all(
    envelopes.map(async (envelope) => {
      const shared = { ...envelope, visibility: 'SHARED' as const };
      await publishShared(shared);
    })
  );
  return envelopes.map((envelope) => ({ ...envelope, visibility: 'SHARED' as const }));
}

async function main() {
  const agenda = promptAgenda();
  const participants = buildParticipants();
  if (participants.length === 0) {
    throw new Error('No model adapter is configured. Set at least one provider API key/model or DEUS_ENDPOINT.');
  }

  const roundId = `round_${new Date().toISOString().replace(/[:.]/g, '-')}_${newId('r').slice(-8)}`;
  console.log(`BL-BRIDGE round: ${roundId}`);
  console.log(`Seats: ${participants.map((p) => p.seat).join(', ')}`);

  const agendaEnvelope = makeEnvelope({
    roundId,
    actor: 'OWNER',
    type: 'AGENDA',
    visibility: 'SHARED',
    content: agenda,
    provenance: {
      provider: 'owner-input',
      model: null,
      adapter_version: 'bl-bridge-runtime/0.1.0',
      runtime_id: null,
      source_refs: []
    }
  });
  await publishShared(agendaEnvelope);

  console.log('Phase: BLIND_PROPOSAL');
  const privateProposals = await callPhase(
    participants,
    roundId,
    'PROPOSAL',
    () => proposalPrompt(agenda),
    [agendaEnvelope.message_id]
  );
  const proposals = await reveal(privateProposals);

  console.log('Phase: CROSS_CRITIQUE');
  const privateCritiques = await callPhase(
    participants,
    roundId,
    'CRITIQUE',
    () => critiquePrompt(agenda, proposals),
    proposals.map((x) => x.message_id)
  );
  const critiques = await reveal(privateCritiques);

  console.log('Phase: REVISION');
  const privateRevisions = await callPhase(
    participants,
    roundId,
    'REVISION',
    () => revisionPrompt(agenda, proposals, critiques),
    [...proposals, ...critiques].map((x) => x.message_id)
  );
  const revisions = await reveal(privateRevisions);

  console.log('Phase: SYNTHESIS / ADJUDICATION');
  const deus = seat(participants, 'DEUS');
  let decision: Envelope;

  if (deus) {
    const content = await deus.respond(synthesisPrompt(agenda, proposals, critiques, revisions), roundId);
    const synthesis = makeEnvelope({
      roundId,
      actor: 'DEUS',
      type: 'SYNTHESIS',
      visibility: 'SHARED',
      content,
      provenance: providerProvenance(deus),
      parentIds: [...proposals, ...critiques, ...revisions].map((x) => x.message_id)
    });
    await publishShared(synthesis);

    decision = makeEnvelope({
      roundId,
      actor: 'DEUS',
      type: 'DECISION',
      visibility: 'SHARED',
      content: `Council synthesis committed. See synthesis message ${synthesis.message_id}. The synthesis text must state the terminal state and preserve material dissent.`,
      provenance: providerProvenance(deus),
      parentIds: [synthesis.message_id]
    });
  } else {
    decision = makeEnvelope({
      roundId,
      actor: 'OWNER',
      type: 'DECISION',
      visibility: 'SHARED',
      content:
        'UNRESOLVED — GPT/Claude/Gemini phases may have completed, but no DEUS endpoint was configured for synthesis/adjudication. The owner can inspect proposals/critiques/revisions or connect DEUS and rerun.',
      provenance: {
        provider: 'bridge-runtime',
        model: null,
        adapter_version: 'bl-bridge-runtime/0.1.0',
        runtime_id: null,
        source_refs: []
      },
      parentIds: revisions.map((x) => x.message_id)
    });
  }

  await publishShared(decision);
  console.log(`Committed: ${decision.message_id}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
