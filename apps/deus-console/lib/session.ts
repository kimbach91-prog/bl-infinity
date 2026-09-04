import 'server-only';
import { cookies } from 'next/headers';
import {
  canAccessSurface,
  validateIdentityAdapterCandidate,
  type VerifiedAccessContext,
  type VerifiedSessionCandidate,
  type VerifiedTenantCandidate,
} from './session-policy.mjs';

export type VerifiedSession = VerifiedSessionCandidate;
export type VerifiedTenant = VerifiedTenantCandidate;
export type { VerifiedAccessContext };

const SESSION_COOKIE = '__Host-deus_session';

/**
 * Server-only identity boundary.
 *
 * Browser state contains only an opaque, HttpOnly session handle. Tenant,
 * roles, scopes, authentication strength, policy version and clearance are
 * resolved by a trusted identity adapter and are never accepted from
 * client-controlled headers, localStorage or request JSON.
 *
 * The adapter response must bind an active enterprise/government tenant to the
 * authenticated session. Weak auth, guest/self-service entry, tenant mismatch,
 * expired sessions and missing role/scope policy all fail closed here before a
 * workspace surface can render.
 */
export async function loadVerifiedAccessContext(): Promise<VerifiedAccessContext | null> {
  const endpoint = process.env.DEUS_IDENTITY_SESSION_ENDPOINT;
  const identityAdapterCredential = process.env.DEUS_IDENTITY_ADAPTER_TOKEN;
  if (!endpoint || !identityAdapterCredential) return null;

  let parsedEndpoint: URL;
  try {
    parsedEndpoint = new URL(endpoint);
  } catch {
    return null;
  }
  if (parsedEndpoint.protocol !== 'https:') return null;

  const cookieStore = await cookies();
  const handle = cookieStore.get(SESSION_COOKIE)?.value;
  if (!handle || handle.length < 32 || handle.length > 512) return null;

  const response = await fetch(parsedEndpoint, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${identityAdapterCredential}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({ sessionHandle: handle }),
    cache: 'no-store',
  });
  if (!response.ok) return null;

  let candidate: unknown;
  try {
    candidate = await response.json();
  } catch {
    return null;
  }

  const verdict = validateIdentityAdapterCandidate(candidate);
  return verdict.ok ? verdict : null;
}

export async function loadVerifiedSession(): Promise<VerifiedSession | null> {
  const context = await loadVerifiedAccessContext();
  return context?.session ?? null;
}

export { canAccessSurface };
export const sessionCookieName = SESSION_COOKIE;
