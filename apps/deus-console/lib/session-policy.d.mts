export type VerifiedTenantCandidate = {
  id: string;
  kind: 'enterprise' | 'government';
  status: 'active';
  requirePhishingResistantAuth?: boolean;
};

export type VerifiedSessionCandidate = {
  authenticated: true;
  identityId: string;
  tenantId: string;
  tenantKind: 'enterprise' | 'government';
  displayName?: string;
  roles: string[];
  scopes: string[];
  policyVersion: string;
  clearance: 'public' | 'internal' | 'confidential' | 'restricted' | 'sovereign';
  authMethods: string[];
  expiresAt: string;
  guest?: boolean;
  anonymous?: boolean;
  signupMode?: string;
};

export type VerifiedAccessContext = {
  ok: true;
  code: 'IDENTITY_CONTEXT_VERIFIED';
  session: VerifiedSessionCandidate;
  tenant: VerifiedTenantCandidate;
};

export function validateIdentityAdapterCandidate(
  candidate: unknown,
  options?: { now?: number },
): VerifiedAccessContext | { ok: false; code: string };

export function canAccessSurface(
  context: VerifiedAccessContext | null | undefined,
  requiredScope: string,
): boolean;

export const webSessionPolicyConstants: Readonly<{
  allowedTenantKinds: string[];
  allowedClearance: string[];
  strongAuthMethods: string[];
  phishingResistantMethods: string[];
}>;
