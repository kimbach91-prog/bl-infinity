import { timingSafeEqual } from 'node:crypto';
import express, { type NextFunction, type Request, type Response } from 'express';
import { config, isSeat } from './config.js';
import { getArtifactText, publishToDrive } from './drive.js';
import { harvest } from './harvester.js';
import { getPendingDeliveries, readControl, updateDeliveryState } from './state.js';
import type { DeliveryState, PublishRequest } from './types.js';

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

app.get('/healthz', (_req, res) => {
  res.json({ ok: true, service: 'deus-cloud-signal-fabric', version: '0.1.0', modelCallsOnIdle: 0 });
});

app.use('/v1', requireSignalAccess);

app.get('/v1/control', async (_req, res, next) => {
  try { res.json({ ok: true, control: await readControl() }); }
  catch (error) { next(error); }
});

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
    const allowed: DeliveryState[] = ['PENDING', 'SEEN', 'WORKING', 'RETURNED', 'FAILED', 'CLOSED'];
    if (!isSeat(seat) || !deliveryId || !allowed.includes(status)) {
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
  console.log(JSON.stringify({ event: 'SIGNAL_FABRIC_LISTENING', port: config.port, appTokenEnabled: Boolean(config.signalToken) }));
});
