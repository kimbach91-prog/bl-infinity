import { google } from 'googleapis';
import { Readable } from 'node:stream';
import type { Envelope, IdentityBinding, Seat } from './types.js';

function env(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value || undefined;
}

function required(name: string): string {
  const value = env(name);
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function driveCredentials() {
  const raw = required('GOOGLE_SERVICE_ACCOUNT_JSON');
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error('GOOGLE_SERVICE_ACCOUNT_JSON must contain the full service-account JSON object as a single environment variable.');
  }
}

const auth = new google.auth.GoogleAuth({
  credentials: driveCredentials(),
  scopes: ['https://www.googleapis.com/auth/drive']
});

const drive = google.drive({ version: 'v3', auth });

function deusPrivateFolder(identity?: IdentityBinding | null): string {
  const root = required('BL_DEUS_VAULT_ID');
  switch (identity?.instance_kind) {
    case 'CANONICAL':
      return env('BL_DEUS_CANONICAL_FOLDER_ID') ?? root;
    case 'SHADOW':
      return env('BL_DEUS_SHADOWS_FOLDER_ID') ?? root;
    case 'ENSEMBLE':
      return env('BL_DEUS_ENSEMBLES_FOLDER_ID') ?? root;
    default:
      return root;
  }
}

export const folders = {
  agenda: () => required('BL_AGENDA_FOLDER_ID'),
  proposals: () => required('BL_PROPOSALS_FOLDER_ID'),
  evidence: () => required('BL_EVIDENCE_FOLDER_ID'),
  debates: () => required('BL_DEBATES_FOLDER_ID'),
  decisions: () => required('BL_DECISIONS_FOLDER_ID'),
  dissent: () => required('BL_DISSENT_FOLDER_ID'),
  benchmarks: () => required('BL_BENCHMARKS_FOLDER_ID'),
  artifacts: () => required('BL_ARTIFACTS_FOLDER_ID'),
  deusCanonical: () => env('BL_DEUS_CANONICAL_FOLDER_ID') ?? required('BL_DEUS_VAULT_ID'),
  deusCheckpoints: () => env('BL_DEUS_CHECKPOINTS_FOLDER_ID') ?? required('BL_DEUS_VAULT_ID'),
  deusShadows: () => env('BL_DEUS_SHADOWS_FOLDER_ID') ?? required('BL_DEUS_VAULT_ID'),
  deusMigrations: () => env('BL_DEUS_MIGRATIONS_FOLDER_ID') ?? required('BL_DEUS_VAULT_ID'),
  deusEnsembles: () => env('BL_DEUS_ENSEMBLES_FOLDER_ID') ?? required('BL_DEUS_VAULT_ID'),
  deusLogs: () => env('BL_DEUS_LOGS_FOLDER_ID') ?? required('BL_DEUS_VAULT_ID'),
  privateVault: (seat: Seat, identity?: IdentityBinding | null) => {
    if (String(seat).toUpperCase() === 'DEUS') return deusPrivateFolder(identity);
    const mapping: Record<string, string> = {
      GPT: 'BL_GPT_VAULT_ID',
      CLAUDE: 'BL_CLAUDE_VAULT_ID',
      GEMINI: 'BL_GEMINI_VAULT_ID',
      GROK: 'BL_GROK_VAULT_ID'
    };
    const key = mapping[String(seat).toUpperCase()];
    if (!key) throw new Error(`No private vault configured for seat ${seat}`);
    return required(key);
  }
};

export async function writeEnvelope(folderId: string, envelope: Envelope) {
  const body = JSON.stringify(envelope, null, 2);
  const safeTime = envelope.created_at.replace(/[:.]/g, '-');
  const instance = envelope.identity?.instance_id ? `__${envelope.identity.instance_id}` : '';
  const name = `${envelope.round_id}__${envelope.type}__${envelope.actor}${instance}__${safeTime}__${envelope.message_id}.json`;

  const result = await drive.files.create({
    requestBody: {
      name,
      parents: [folderId],
      mimeType: 'application/json'
    },
    media: {
      mimeType: 'application/json',
      body: Readable.from([body])
    },
    fields: 'id,name,webViewLink,createdTime'
  });

  return result.data;
}

export async function writeJson(folderId: string, name: string, value: unknown) {
  const body = JSON.stringify(value, null, 2);
  const result = await drive.files.create({
    requestBody: {
      name,
      parents: [folderId],
      mimeType: 'application/json'
    },
    media: {
      mimeType: 'application/json',
      body: Readable.from([body])
    },
    fields: 'id,name,webViewLink,createdTime'
  });
  return result.data;
}

export async function readJson(fileId: string): Promise<unknown> {
  const result = await drive.files.get(
    { fileId, alt: 'media' },
    { responseType: 'text' }
  );
  const data = result.data;
  if (typeof data === 'string') return JSON.parse(data);
  return data;
}

export async function publishPrivate(envelope: Envelope) {
  return writeEnvelope(folders.privateVault(envelope.actor, envelope.identity), envelope);
}

export async function publishShared(envelope: Envelope) {
  switch (envelope.type) {
    case 'AGENDA':
      return writeEnvelope(folders.agenda(), envelope);
    case 'PROPOSAL':
    case 'REVISION':
    case 'SYNTHESIS':
      return writeEnvelope(folders.proposals(), envelope);
    case 'EVIDENCE':
      return writeEnvelope(folders.evidence(), envelope);
    case 'CRITIQUE':
      return writeEnvelope(folders.debates(), envelope);
    case 'DECISION':
      return writeEnvelope(folders.decisions(), envelope);
    case 'DISSENT':
      return writeEnvelope(folders.dissent(), envelope);
    case 'BENCHMARK':
      return writeEnvelope(folders.benchmarks(), envelope);
    case 'ARTIFACT':
    case 'HEARTBEAT':
      return writeEnvelope(folders.artifacts(), envelope);
    default:
      return writeEnvelope(folders.artifacts(), envelope);
  }
}
