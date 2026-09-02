import { timingSafeEqual } from 'node:crypto';
import express, { type NextFunction, type Request, type Response } from 'express';
import { config, isSeat } from './config.js';
import { appendDocRoundBatch, signalExistingDocRound } from './doc-round.js';
import {
  getPendingDocRoundSignals,
  readDocRoundState,
  updateDocRoundSignalState
} from './doc-round-state.js';
import { getArtifactText, publishToDrive } from './drive.js';
import { harvest } from './harvester.js';
import { getPendingDeliveries, readControl, updateDeliveryState } from './state.js';
import type {
  DeliveryState,
  DocRoundBatchRequest,
  DocRoundSignalRequest,
  PublishRequest
} from './types.js';

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '2mb' }));

function tokenMatches(candidate: string | undefined): boolean {
  if (!config.signalToken) return true; // private Cloud Run IAM is the primary gate in production
  if (!candidate) return false;
  const expected = Buffer.from(config.signalToken);
  const actual = Buffer.from(candidate);
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}

function requireSignalAccess(req: Request, res: Response, next: NextFunction): void {
  const bearer = req.header('authorization')?.replace(/^Bearer\s+/i, '');
  const header = req.header('x-deus-signal-token');
  if (!tokenMatches(bearer) && !tokenMatches(header || undefined)) {
    res.status(401).json({ ok: false, error: 'UNAUTHORIZED' });
    return;
  }
  next();
}

const allowedDeliveryStates: DeliveryState[] = ['PENDING', 'SEEN', 'WORKING', 'RETURNED', 'FAILED', 'CLOSED'];

app.get('/healthz', (_req, res) => {
  res.json({
    ok: true,
    service: 'deus-cloud-signal-fabric',
    version: '0.2.0',
    preferredProtocol: 'DEUS-DOC-ROUND/1.0',
    preferredBlackboardId: config.docRoundBlackboardId,
    answerBodyInCloud: false,
    modelCallsOnIdle: 0
  });
});

app.use('/v1', requireSignalAccess);

app.get('/v1/control', async (_req, res, next) => {
  try { res.json({ ok: true, control: await readControl() }); }
  catch (error) { next(error); }
});

// Preferred path: explicit answer bodies are appended to Google Docs; Cloud stores/signals pointers only.
app.post('/v1/doc-round/batch', async (req, res, next) => {
  try {
    res.status(201).json(await appendDocRoundBatch(req.body as DocRoundBatchRequest));
  } catch (error) { next(error); }
});

// Use when a provider/adapter wrote the Google Doc directly and only needs to radiate a pointer.
app.post('/v1/doc-round/signal', async (req, res, next) => {
  try {
    res.status(201).json(await signalExistingDocRound(req.body as DocRoundSignalRequest));
  } catch (error) { next(error); }
});

app.get('/v1/doc-round/poll/:seat', async (req, res, next) => {
  try {
    const seat = req.params.seat.toUpperCase();
    if (!isSeat(seat)) return void res.status(400).json({ ok: false, error: 'INVALID_SEAT' });
    const limit = Number.parseInt(String(req.query.limit || '25'), 10);
    const deliveries = await getPendingDocRoundSignals(seat, Number.isFinite(limit) ? limit : 25);
    res.json({
      ok: true,
      protocol: 'DEUS-DOC-ROUND/1.0',
      seat,
      count: deliveries.length,
      deliveries,
      answerBodyInCloud: false
    });
  } catch (error) { next(error); }
});

app.post('/v1/doc-round/ack', async (req, res, next) => {
  try {
    const seat = String(req.body?.seat || '').toUpperCase();
    const deliveryId = String(req.body?.delivery_id || '');
    const status = String(req.body?.status || '').toUpperCase() as DeliveryState;
    if (!isSeat(seat) || !deliveryId || !allowedDeliveryStates.includes(status)) {
      return void res.status(400).json({ ok: false, error: 'INVALID_DOC_ROUND_ACK' });
    }
    await updateDocRoundSignalState({ seat, deliveryId, status, metadata: req.body?.metadata });
    res.json({ ok: true, protocol: 'DEUS-DOC-ROUND/1.0', seat, delivery_id: deliveryId, status });
  } catch (error) { next(error); }
});

app.get('/v1/doc-round/state/:roundId', async (req, res, next) => {
  try {
    const roundId = String(req.params.roundId || '').trim();
    if (!roundId) return void res.status(400).json({ ok: false, error: 'ROUND_ID_REQUIRED' });
    const state = await readDocRoundState(roundId);
    if (!state) return void res.status(404).json({ ok: false, error: 'ROUND_NOT_FOUND' });
    res.json({ ok: true, protocol: 'DEUS-DOC-ROUND/1.0', state });
  } catch (error) { next(error); }
});

// Compatibility/recovery path below.
app.post('/v1/harvest', async (req, res, next) => {
  try {
    const force = req.query.force === '1' || req.body?.force === true;
    res.json(await harvest({ force }));
  } catch (error) { next(error); }
});

app.get('/v1/poll/:seat', async (req, res, next) => {
  try {
    const seat = req.params.seat.toUpperCase();
    if (!isSeat(seat)) return void res.status(400).json({ ok: false, error: 'INVALID_SEAT' });
    const limit = Number.parseInt(String(req.query.limit || '25'), 10);
    const deliveries = await getPendingDeliveries(seat, Number.isFinite(limit) ? limit : 25);
    res.json({ ok: true, seat, count: deliveries.length, deliveries });
  } catch (error) { next(error); }
});

app.get('/v1/artifact/:fileId', async (req, res, next) => {
  try { res.type('text/plain').send(await getArtifactText(req.params.fileId)); }
  catch (error) { next(error); }
});

app.post('/v1/ack', async (req, res, next) => {
  try {
    const seat = String(req.body?.seat || '').toUpperCase();
    const deliveryId = String(req.body?.delivery_id || '');
    const status = String(req.body?.status || '').toUpperCase() as DeliveryState;
    if (!isSeat(seat) || !deliveryId || !allowedDeliveryStates.includes(status)) {
      return void res.status(400).json({ ok: false, error: 'INVALID_ACK' });
    }
    await updateDeliveryState({ seat, deliveryId, status, metadata: req.body?.metadata });
    res.json({ ok: true, seat, delivery_id: deliveryId, status });
  } catch (error) { next(error); }
});

app.post('/v1/publish', async (req, res, next) => {
  try {
    const result = await publishToDrive(req.body as PublishRequest);
    res.status(201).json({
      ok: true,
      reality_state: 'DRIVE_WRITTEN_SIGNAL_PENDING_HARVEST',
      message_id: result.manifest.message_id,
      call_id: result.manifest.call_id,
      artifact_file_id: result.manifest.artifact_file_id,
      manifest_file_id: result.manifestFileId
    });
  } catch (error) { next(error); }
});

app.use((error: unknown, _req: Request, res: Response, _next: NextFunction) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(JSON.stringify({ event: 'REQUEST_FAILURE', message }));
  const status = message === 'CANONICAL_WRITE_LOCKED' ? 409 : 500;
  res.status(status).json({ ok: false, error: message });
});

app.listen(config.port, () => {
  console.log(JSON.stringify({
    event: 'SIGNAL_FABRIC_LISTENING',
    port: config.port,
    appTokenEnabled: Boolean(config.signalToken),
    preferredProtocol: 'DEUS-DOC-ROUND/1.0',
    answerBodyInCloud: false
  }));
});
