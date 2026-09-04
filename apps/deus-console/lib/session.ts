import 'server-only';

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

/**
 * Server-only session adapter boundary.
 *
 * The browser is never trusted to assert tenant, roles, scopes or clearance.
 * Until a production IdP adapter is configured, this function fails closed.
 */
export async function loadVerifiedSession(): Promise<VerifiedSession | null> {
  const endpoint = process.env.DEUS_IDENTITY_SESSION_ENDPOINT;
  const audienceToken = process.env.DEUS_IDENTITY_ADAPTER_TOKEN;
  if (!endpoint || !audienceToken) return null;

  const response = await fetch(endpoint, {
    method: 'GET',
    headers: { authorization: `Bearer ${audienceToken}` },
    cache: 'no-store',
  });
  if (!response.ok) return null;

  const candidate = await response.json();
  if (!candidate || candidate.verified !== true || !candidate.session) return null;

  const session = candidate.session as VerifiedSession;
  if (!session.identityId || !session.tenantId) return null;
  if (!['enterprise', 'government'].includes(session.tenantKind)) return null;
  if (!Array.isArray(session.roles) || !Array.isArray(session.scopes) || !Array.isArray(session.authMethods)) return null;
  if (!session.expiresAt || Date.parse(session.expiresAt) <= Date.now()) return null;

  return session;
}
