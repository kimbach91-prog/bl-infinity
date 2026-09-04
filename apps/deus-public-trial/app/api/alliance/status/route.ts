import { publicAlliancePolicy } from '../../../../lib/alliance-policy';

export const dynamic = 'force-dynamic';

export async function GET() {
  return Response.json({
    surface: 'DEUS_PUBLIC_TRIAL',
    policy: publicAlliancePolicy,
    runtime: {
      localPromptBoundContribution: 'ACTIVE',
      publicInferenceCortex: process.env.AI_GATEWAY_API_KEY || process.env.VERCEL_OIDC_TOKEN ? 'BOUND' : 'NOT_BOUND',
      crossNodeBroker: process.env.DEUS_ALLIANCE_BROKER_URL ? 'CONFIGURED_UNVERIFIED' : 'STAGED_NOT_BOUND',
      durableCreditLedger: 'STAGED_NOT_BOUND',
    },
    evidenceSemantics: {
      configuredDoesNotMeanExecuted: true,
      noCrossNodeClaimWithoutReceipt: true,
    },
  }, { headers: { 'cache-control': 'no-store' } });
}
