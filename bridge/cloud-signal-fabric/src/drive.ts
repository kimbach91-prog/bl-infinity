import { createHash, randomUUID } from 'node:crypto';
import { Readable } from 'node:stream';
import { google, drive_v3 } from 'googleapis';
import { config, isSeat, type Seat } from './config.js';
import type { MailboxManifest, PublishRequest } from './types.js';

const auth = new google.auth.GoogleAuth({ scopes: ['https://www.googleapis.com/auth/drive'] });
export const drive = google.drive({ version: 'v3', auth });

export interface ManifestChange {
  fileId: string;
  version?: string | null;
  modifiedTime?: string | null;
}

export function validateManifest(value: unknown): MailboxManifest {
  if (!value || typeof value !== 'object') throw new Error('Manifest must be an object');
  const m = value as Partial<MailboxManifest>;
  if (m.protocol !== 'DEUS-MAILBOX/1.0') throw new Error('Unsupported manifest protocol');
  if (!m.message_id || !m.call_id || !m.message_type || !m.created_at || !m.artifact_file_id) throw new Error('Manifest missing required identifiers');
  if (!isSeat(m.from)) throw new Error('Invalid manifest sender');
  if (!Array.isArray(m.to) || m.to.length === 0 || !m.to.every(isSeat)) throw new Error('Invalid manifest audience');
  if (m.authority !== 'CANDIDATE_ONLY' && m.authority !== 'CANONICAL') throw new Error('Invalid authority');
  return m as MailboxManifest;
}

export async function getStartCursor(): Promise<string> {
  const result = await drive.changes.getStartPageToken({ supportsAllDrives: true });
  if (!result.data.startPageToken) throw new Error('Drive did not return startPageToken');
  return result.data.startPageToken;
}

export async function listManifestChanges(pageToken: string): Promise<{ changes: ManifestChange[]; nextCursor: string }> {
  const result = await drive.changes.list({
    pageToken,
    pageSize: config.changePageSize,
    includeItemsFromAllDrives: true,
    supportsAllDrives: true,
    spaces: 'drive',
    fields: 'nextPageToken,newStartPageToken,changes(fileId,removed,file(id,name,mimeType,parents,version,modifiedTime,trashed))'
  });

  const changes: ManifestChange[] = [];
  for (const change of result.data.changes || []) {
    const file = change.file;
    if (change.removed || !file || file.trashed || !file.id) continue;
    if (!(file.parents || []).includes(config.manifestFolderId)) continue;
    if (!file.name?.endsWith('.manifest.json')) continue;
    changes.push({ fileId: file.id, version: file.version || null, modifiedTime: file.modifiedTime || null });
  }

  const nextCursor = result.data.nextPageToken || result.data.newStartPageToken;
  if (!nextCursor) throw new Error('Drive changes.list returned no continuation cursor');
  return { changes, nextCursor };
}

export async function readManifest(fileId: string): Promise<MailboxManifest> {
  const result = await drive.files.get({ fileId, alt: 'media', supportsAllDrives: true }, { responseType: 'text' });
  const raw = typeof result.data === 'string' ? result.data : JSON.stringify(result.data);
  return validateManifest(JSON.parse(raw));
}

function assertPublishRequest(req: PublishRequest): void {
  if (!isSeat(req.from)) throw new Error('Invalid sender');
  if (!Array.isArray(req.to) || req.to.length === 0 || !req.to.every(isSeat)) throw new Error('Invalid audience');
  if (!req.call_id?.trim()) throw new Error('call_id is required');
  if (!req.artifact_text?.trim()) throw new Error('artifact_text is required');
  if (req.authority === 'CANONICAL' || req.message_type === 'CANON_COMMIT') {
    if (process.env.CANONICAL_WRITE_ENABLED !== 'true') throw new Error('CANONICAL_WRITE_LOCKED');
    if (req.from !== 'DEUS') throw new Error('Only DEUS may request canonical publish');
  }
}

export async function publishToDrive(req: PublishRequest): Promise<{ manifest: MailboxManifest; manifestFileId: string }> {
  assertPublishRequest(req);
  const createdAt = new Date().toISOString();
  const messageId = `msg_${randomUUID()}`;
  const safeCall = req.call_id.replace(/[^A-Za-z0-9_.-]/g, '_');
  const safeFrom = req.from.replace(/[^A-Za-z0-9_.-]/g, '_');
  const safeType = req.message_type.replace(/[^A-Za-z0-9_.-]/g, '_');
  const artifactName = req.artifact_name?.trim() || `${createdAt.replace(/[:.]/g, '-')}__${safeCall}__${safeFrom}__${safeType}.txt`;
  const mimeType = req.artifact_mime_type?.trim() || 'text/plain';
  const digest = createHash('sha256').update(req.artifact_text, 'utf8').digest('hex');

  const artifact = await drive.files.create({
    requestBody: { name: artifactName, parents: [config.artifactFolderId], mimeType },
    media: { mimeType, body: Readable.from([req.artifact_text]) },
    supportsAllDrives: true,
    fields: 'id,version,modifiedTime'
  });
  if (!artifact.data.id) throw new Error('Drive artifact write returned no file id');

  const manifest: MailboxManifest = {
    protocol: 'DEUS-MAILBOX/1.0',
    message_id: messageId,
    call_id: req.call_id,
    message_type: req.message_type,
    from: req.from as Seat,
    to: req.to as Seat[],
    created_at: createdAt,
    artifact_file_id: artifact.data.id,
    artifact_revision: artifact.data.version || null,
    artifact_sha256: digest,
    parent_message_id: req.parent_message_id || null,
    authority: req.authority || 'CANDIDATE_ONLY',
    requires_ack: req.requires_ack ?? true,
    expires_at: null,
    metadata: req.metadata || {}
  };

  const manifestBody = JSON.stringify(manifest, null, 2);
  const manifestWrite = await drive.files.create({
    requestBody: {
      name: `${createdAt.replace(/[:.]/g, '-')}__${messageId}.manifest.json`,
      parents: [config.manifestFolderId],
      mimeType: 'application/json'
    },
    media: { mimeType: 'application/json', body: Readable.from([manifestBody]) },
    supportsAllDrives: true,
    fields: 'id'
  });
  if (!manifestWrite.data.id) throw new Error('Drive manifest write returned no file id');
  return { manifest, manifestFileId: manifestWrite.data.id };
}

export async function getArtifactText(fileId: string): Promise<string> {
  const result = await drive.files.get({ fileId, alt: 'media', supportsAllDrives: true }, { responseType: 'text' });
  return typeof result.data === 'string' ? result.data : JSON.stringify(result.data);
}

export type DriveFile = drive_v3.Schema$File;
