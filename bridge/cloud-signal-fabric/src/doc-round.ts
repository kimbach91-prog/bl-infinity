import { google } from 'googleapis';
import { config, isSeat } from './config.js';
import { publishDocRoundSignal } from './doc-round-state.js';
import type {
  DocRoundBatchRequest,
  DocRoundContribution,
  DocRoundSignalRequest
} from './types.js';

const auth = new google.auth.GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
});

const docs = google.docs({ version: 'v1', auth });

function nonEmpty(value: unknown, name: string): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${name} is required`);
  return value.trim();
}

function validateAudience(value: unknown): asserts value is DocRoundBatchRequest['to'] {
  if (!Array.isArray(value) || value.length === 0 || !value.every(isSeat)) {
    throw new Error('Doc-round audience must contain at least one valid seat');
  }
}

function validateContribution(value: DocRoundContribution): void {
  if (!value || !isSeat(value.actor)) throw new Error('Invalid contribution actor');
  if (typeof value.final_text !== 'string' || !value.final_text.trim()) {
    throw new Error(`Empty final_text for actor ${String(value.actor)}`);
  }
}

function assertSignalType(value: unknown): void {
  if (!['ROUND_READY', 'REVIEW_REQUIRED', 'FINAL_READY', 'ROUND_CLOSED'].includes(String(value))) {
    throw new Error('Invalid DOC-ROUND signal_type');
  }
}

function assertRoundState(value: unknown): void {
  if (!['CANDIDATE', 'REVIEW', 'FINAL', 'CLOSED'].includes(String(value))) {
    throw new Error('Invalid DOC-ROUND state');
  }
}

function formatContribution(contribution: DocRoundContribution): string {
  return `[ACTOR ${contribution.actor}]\n${contribution.final_text.trim()}\n[/ACTOR]\n`;
}

function formatRoundBlock(req: DocRoundBatchRequest): string {
  const header = `[ROUND ${req.round_id} | TENANT ${req.tenant_id} | TASK ${req.task_id} | SIGNAL ${req.signal_type} | STATE ${req.state}]\n`;
  return `\n${header}${req.contributions.map(formatContribution).join('')}[END ROUND ${req.round_id}]\n`;
}

function normalizeSignal(req: DocRoundSignalRequest): DocRoundSignalRequest {
  const roundId = nonEmpty(req.round_id, 'round_id');
  const tenantId = nonEmpty(req.tenant_id, 'tenant_id');
  const taskId = nonEmpty(req.task_id, 'task_id');
  if (!isSeat(req.from)) throw new Error('Invalid signal sender');
  validateAudience(req.to);
  assertSignalType(req.signal_type);
  assertRoundState(req.state);

  return {
    ...req,
    round_id: roundId,
    tenant_id: tenantId,
    task_id: taskId,
    document_id: req.document_id?.trim() || config.docRoundBlackboardId,
    marker: req.marker?.trim() || `[ROUND ${roundId}`
  };
}

export async function appendDocRoundBatch(raw: DocRoundBatchRequest): Promise<Record<string, unknown>> {
  const req: DocRoundBatchRequest = {
    ...raw,
    round_id: nonEmpty(raw.round_id, 'round_id'),
    tenant_id: nonEmpty(raw.tenant_id, 'tenant_id'),
    task_id: nonEmpty(raw.task_id, 'task_id'),
    document_id: raw.document_id?.trim() || config.docRoundBlackboardId
  };

  if (!isSeat(req.from)) throw new Error('Invalid batch sender');
  validateAudience(req.to);
  assertSignalType(req.signal_type);
  assertRoundState(req.state);
  if (!Array.isArray(req.contributions) || req.contributions.length === 0) {
    throw new Error('At least one contribution is required');
  }
  req.contributions.forEach(validateContribution);

  const block = formatRoundBlock(req);
  const write = await docs.documents.batchUpdate({
    documentId: req.document_id!,
    requestBody: {
      requests: [{
        insertText: {
          endOfSegmentLocation: { tabId: config.docRoundTabId },
          text: block
        }
      }]
    }
  });

  const revisionId = write.data.writeControl?.requiredRevisionId || null;
  const signal: DocRoundSignalRequest = normalizeSignal({
    round_id: req.round_id,
    tenant_id: req.tenant_id,
    task_id: req.task_id,
    from: req.from,
    to: req.to,
    signal_type: req.signal_type,
    state: req.state,
    document_id: req.document_id,
    marker: `[ROUND ${req.round_id}`,
    doc_revision_id: revisionId,
    metadata: {
      ...(req.metadata || {}),
      contributor_actors: [...new Set(req.contributions.map((item) => item.actor))],
      contribution_count: req.contributions.length,
      write_mode: 'DOCS_BATCH_APPEND',
      answer_body_in_cloud: false
    }
  });

  const deliveries = await publishDocRoundSignal(signal);
  return {
    ok: true,
    protocol: 'DEUS-DOC-ROUND/1.0',
    reality_state: 'DOC_WRITTEN_SIGNAL_EMITTED',
    round_id: req.round_id,
    document_id: req.document_id,
    doc_revision_id: revisionId,
    marker: signal.marker,
    signal_type: req.signal_type,
    state: req.state,
    deliveries: deliveries.length,
    docs_write_requests: 1,
    cloud_answer_bytes: 0
  };
}

export async function signalExistingDocRound(raw: DocRoundSignalRequest): Promise<Record<string, unknown>> {
  const signal = normalizeSignal(raw);
  const deliveries = await publishDocRoundSignal(signal);
  return {
    ok: true,
    protocol: 'DEUS-DOC-ROUND/1.0',
    reality_state: 'POINTER_SIGNAL_EMITTED',
    round_id: signal.round_id,
    document_id: signal.document_id,
    marker: signal.marker,
    signal_type: signal.signal_type,
    state: signal.state,
    deliveries: deliveries.length,
    cloud_answer_bytes: 0
  };
}
