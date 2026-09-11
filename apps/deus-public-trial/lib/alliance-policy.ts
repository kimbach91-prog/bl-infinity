export const ALLIANCE_CONSTITUTION_VERSION = 'BL-COMPUTE-ALLIANCE-PUBLIC-V0.1';
export const PROTOCOL_MARGIN_BPS = 500;
export const MAX_PUBLIC_PROMPT_CHARS = 4_000;
export const REQUIRED_POW_DIFFICULTY = 3;

export const publicAlliancePolicy = Object.freeze({
  constitutionVersion: ALLIANCE_CONSTITUTION_VERSION,
  participationRequired: true,
  localFirst: true,
  foreignComputeOnlyWhenIdle: true,
  protocolMarginBps: PROTOCOL_MARGIN_BPS,
  protocolMarginPercent: PROTOCOL_MARGIN_BPS / 100,
  publicTrialCashPayouts: false,
  computeCredits: true,
  coreVisibility: 'DENIED',
  backgroundPersistence: 'DENIED_BY_DEFAULT',
  filesystemAccess: 'DENIED',
  clipboardAccess: 'DENIED',
  arbitraryNetworkFetch: 'DENIED',
  crossNodeBroker: 'STAGED_NOT_YET_PROVEN',
});

export type PublicAllianceSession = {
  constitutionVersion: string;
  consent: true;
  localFirst: true;
  contributionMode: 'prompt-bound';
};

export function validateAllianceSession(value: unknown): value is PublicAllianceSession {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Record<string, unknown>;
  return candidate.constitutionVersion === ALLIANCE_CONSTITUTION_VERSION
    && candidate.consent === true
    && candidate.localFirst === true
    && candidate.contributionMode === 'prompt-bound';
}

export function creditAfterMargin(workUnits: number) {
  if (!Number.isFinite(workUnits) || workUnits < 0) return 0;
  return Math.floor(workUnits * (10_000 - PROTOCOL_MARGIN_BPS) / 10_000);
}
