export type Seat = 'DEUS' | 'CLAUDE' | 'GEMINI' | 'GROK';

const required = (name: string): string => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
};

const integer = (name: string, fallback: number): number => {
  const raw = process.env[name]?.trim();
  if (!raw) return fallback;
  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value) || value < 1) throw new Error(`Invalid positive integer for ${name}`);
  return value;
};

export const config = {
  port: Number.parseInt(process.env.PORT || '8080', 10),
  projectId: process.env.GOOGLE_CLOUD_PROJECT?.trim() || process.env.GCLOUD_PROJECT?.trim(),
  signalToken: process.env.SIGNAL_FABRIC_TOKEN?.trim() || null,

  // Compatibility/recovery path.
  manifestFolderId: required('DRIVE_MANIFEST_FOLDER_ID'),
  artifactFolderId: required('DRIVE_ARTIFACTS_ID'),

  // Preferred low-cost DOC-ROUND path.
  docRoundBlackboardId: process.env.DOC_ROUND_BLACKBOARD_ID?.trim() || '1tm0RSqvleIrxmksh5pyn_EI1nquf7bbYgoxHqcQ3tFU',
  docRoundFolderId: process.env.DOC_ROUND_FOLDER_ID?.trim() || '13j-y0oY2cubo3Me0PN1DqMT0Ub3ag2xk',
  docRoundTabId: process.env.DOC_ROUND_TAB_ID?.trim() || 't.0',

  hotMinutes: integer('POLL_HOT_MINUTES', 1),
  warmMinutes: integer('POLL_WARM_MINUTES', 3),
  idleMinutes: integer('POLL_IDLE_MINUTES', 5),
  hotWindowMinutes: integer('HOT_WINDOW_MINUTES', 10),
  warmWindowMinutes: integer('WARM_WINDOW_MINUTES', 30),
  changePageSize: Math.min(integer('DRIVE_CHANGE_PAGE_SIZE', 100), 100),
  leaseSeconds: integer('HARVEST_LEASE_SECONDS', 50)
};

export const seats: Seat[] = ['DEUS', 'CLAUDE', 'GEMINI', 'GROK'];

export function isSeat(value: unknown): value is Seat {
  return typeof value === 'string' && seats.includes(value.toUpperCase() as Seat);
}
