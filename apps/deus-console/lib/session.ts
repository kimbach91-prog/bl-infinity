import 'server-only';
import { cookies } from 'next/headers';

export type VerifiedSession = {
  identityId: string;
  tenantId: string;
  tenantKind: 'enterprise' | 'government';
  displayName?: string;
  roles: string[];
  scopes: string[];
  clearance: 'public' | 'internal' | 'confidential' | 'restricted' | 'sovereign';
  authMethods: string[];
  expiresAt: string;
};

const SESSION_COOKIE = '__Host-deus_session';

/**
 * Server-only session adapter boundary.
 *
 * Browser state contains only an opaque, HttpOnly session handle. Tenant,
 * roles, scopes, authentication strength and clearance are resolved by a
 * trusted identity adapter and are never accepted from client-controlled
 * headers, localStorage or request JSON.
 *
 * Until a production identity adapter and opaque session are configured, this
 * function fails closed.
 */
export async function loadVerifiedSession(): Promise<VerifiedSession | null> {
  const endpoint = process.env.DEUS_IDENTITY_SESSION_ENDPOINT;
  const adapterToken = process.env.DEUS_IDENTITY_ADAPTER_TOKEN;
  if (!endpoint || !adapterToken) return null;

  const cookieStore = await cookies();
  const handle = cookieStore.get(SESSION_COOKIE)?.value;
  if (!handle || handle.length < 32 || handle.length > 512) return null;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${adapterToken}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({ sessionHandle: handle }),
    cache: 'no-store',
  });
  if (!response.ok) return null;

  const candidate = await response.json();
  if (!candidate || candidate.verified !== true || !candidate.session) return null;

  const session = candidate.session as VerifiedSession;
  if (!session.identityId || !session.tenantId) return null;
  if (!['enterprise', 'government'].includes(session.tenantKind)) return null;
  if (!Array.isArray(session.roles) || session.roles.length === 0) return null;
  if (!Array.isArray(session.scopes) || !Array.isArray(session.authMethods)) return null;
  if (!session.expiresAt || Date.parse(session.expiresAt) <= Date.now()) return null;

  return session;
}

export const sessionCookieName = SESSION_COOKIE;
