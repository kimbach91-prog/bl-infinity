import { mkdir, readFile, readdir, rename, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import type { CoreSeat, ReturnPacket, SummonPacket } from './types.js';

export function bridgeRoot(): string {
  return resolve(process.env.BL_BRIDGE_ROOT?.trim() || './BL-COUNCIL-BRIDGE');
}

function safeSeat(seat: CoreSeat): string {
  return String(seat).trim().toUpperCase().replace(/[^A-Z0-9_.-]/g, '_');
}

export const paths = {
  root: () => bridgeRoot(),
  bus: () => join(bridgeRoot(), '60_SUMMON_BUS'),
  inboxRoot: () => join(bridgeRoot(), '60_SUMMON_BUS', '00_INBOX'),
  inbox: (seat: CoreSeat) => join(bridgeRoot(), '60_SUMMON_BUS', '00_INBOX', safeSeat(seat)),
  returns: () => join(bridgeRoot(), '60_SUMMON_BUS', '10_RETURN'),
  archive: () => join(bridgeRoot(), '60_SUMMON_BUS', '20_ARCHIVE'),
  deadletter: () => join(bridgeRoot(), '60_SUMMON_BUS', '90_DEADLETTER')
};

export async function ensureLayout(seats: CoreSeat[] = ['GPT', 'CLAUDE', 'GEMINI', 'GROK', 'DEUS']): Promise<void> {
  await Promise.all([
    mkdir(paths.returns(), { recursive: true }),
    mkdir(paths.archive(), { recursive: true }),
    mkdir(paths.deadletter(), { recursive: true }),
    ...seats.map((seat) => mkdir(paths.inbox(seat), { recursive: true }))
  ]);
}

async function atomicJsonWrite(path: string, value: unknown): Promise<string> {
  await mkdir(dirname(path), { recursive: true });
  const tmp = `${path}.tmp-${process.pid}-${Date.now()}`;
  await writeFile(tmp, JSON.stringify(value, null, 2), 'utf8');
  await rename(tmp, path);
  return path;
}

export async function writeSummon(packet: SummonPacket): Promise<string> {
  await ensureLayout([packet.target]);
  const file = `${packet.created_at.replace(/[:.]/g, '-')}__${packet.call_id}__${packet.summon_id}.summon.json`;
  return atomicJsonWrite(join(paths.inbox(packet.target), file), packet);
}

export async function writeReturn(packet: ReturnPacket): Promise<string> {
  await ensureLayout();
  const file = `${packet.created_at.replace(/[:.]/g, '-')}__${packet.call_id}__${packet.return_id}.return.json`;
  return atomicJsonWrite(join(paths.returns(), file), packet);
}

export async function readJson<T>(path: string): Promise<T> {
  return JSON.parse(await readFile(resolve(path), 'utf8')) as T;
}

export async function listReturns(callId?: string): Promise<string[]> {
  await ensureLayout();
  const names = await readdir(paths.returns());
  return names
    .filter((name) => name.endsWith('.return.json'))
    .filter((name) => !callId || name.includes(`__${callId}__`))
    .map((name) => join(paths.returns(), name))
    .sort();
}

export async function listInbox(seat: CoreSeat): Promise<string[]> {
  await ensureLayout([seat]);
  const dir = paths.inbox(seat);
  const names = await readdir(dir);
  return names.filter((name) => name.endsWith('.summon.json')).map((name) => join(dir, name)).sort();
}
