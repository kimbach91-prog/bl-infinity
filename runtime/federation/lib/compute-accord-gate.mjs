import { createHash } from 'node:crypto';

export const COMPUTE_ACCORD_GATE_VERSION='deus-compute-accord-gate/1.0';

const AUTHORIZED_CLASSES=new Set([
  'OWNER_AUTHORIZED',
  'CONNECTED_ACCOUNT',
  'PUBLIC_SERVICE_INTENDED',
  'OPT_IN_MARKET',
  'OPT_IN_VOLUNTEER',
  'OPT_IN_SERVICE',
]);

function n(v,fallback=0){
  const x=Number(v);
  return Number.isFinite(x)?x:fallback;
}
function b(v){return v===true;}
function s(v){return v==null?'':String(v);}
function digest(value){
  return createHash('sha256').update(JSON.stringify(value,Object.keys(value).sort())).digest('hex');
}

export function normalizeComputeOffer(raw={}){
  const offer={
    schema:'deus-compute-offer/1',
    offerId:s(raw.offerId||raw.routeId||raw.provider||'unknown'),
    provider:s(raw.provider||'unknown'),
    routeId:s(raw.routeId||raw.offerId||'unknown'),
    authorityClass:s(raw.authorityClass||'UNKNOWN').toUpperCase(),
    capabilityClass:s(raw.capabilityClass||'OTHER'),
    dataClassMax:s(raw.dataClassMax||'BL-S0'),
    freshnessMs:n(raw.freshnessMs,Infinity),
    freshnessLimitMs:n(raw.freshnessLimitMs,3600000),
    receiptPath:b(raw.receiptPath),
    canaryPassed:b(raw.canaryPassed),
    currentLease:b(raw.currentLease),
    publicIntended:b(raw.publicIntended),
    optIn:b(raw.optIn),
    ownerAuthorized:b(raw.ownerAuthorized),
    installMode:s(raw.installMode||'NONE').toUpperCase(),
    installConsent:b(raw.installConsent),
    expectedUsefulValue:n(raw.expectedUsefulValue,0),
    expectedRevenue:n(raw.expectedRevenue,0),
    computeCost:n(raw.computeCost,0),
    bandwidthCost:n(raw.bandwidthCost,0),
    settlementCost:n(raw.settlementCost,0),
    coordinationCost:n(raw.coordinationCost,0),
    energyMetricKnown:b(raw.energyMetricKnown),
    energyCost:n(raw.energyCost,0),
    economicAuthority:b(raw.economicAuthority),
    paymentRequired:b(raw.paymentRequired),
    revenueSharePct:n(raw.revenueSharePct,0),
    quotaKnown:b(raw.quotaKnown),
    availabilityKnown:b(raw.availabilityKnown),
    metadata:raw.metadata??{},
  };
  return Object.freeze({...offer,offerDigest:digest(offer)});
}

export function evaluateComputeOffer(raw={},policy={}){
  const o=normalizeComputeOffer(raw);
  const maxFresh=n(policy.maxFreshAgeMs,o.freshnessLimitMs);
  const minMargin=n(policy.minExpectedNetMargin,0);
  const net=o.expectedRevenue+o.expectedUsefulValue-o.computeCost-o.bandwidthCost-o.settlementCost-o.coordinationCost-(o.energyMetricKnown?o.energyCost:0);
  const reasons=[];

  const authorityOkay=AUTHORIZED_CLASSES.has(o.authorityClass)
    && (o.ownerAuthorized||o.optIn||o.publicIntended||o.authorityClass==='CONNECTED_ACCOUNT');
  if(!authorityOkay) reasons.push('NO_VALID_AUTHORITY_OR_OPT_IN_CONTRACT');

  if(o.installMode!=='NONE' && !o.installConsent) reasons.push('INSTALL_CONSENT_MISSING');
  if(!o.receiptPath) reasons.push('NO_ATTRIBUTABLE_RECEIPT_PATH');
  if(o.freshnessMs>maxFresh) reasons.push('STALE_ROUTE_EVIDENCE');
  if(o.paymentRequired && !o.economicAuthority) reasons.push('ECONOMIC_AUTHORITY_REQUIRED');
  if(o.paymentRequired && net<minMargin) reasons.push('EXPECTED_NET_MARGIN_BELOW_POLICY');

  let decision='OFFER_CANDIDATE';
  if(reasons.some(x=>x==='NO_VALID_AUTHORITY_OR_OPT_IN_CONTRACT'||x==='INSTALL_CONSENT_MISSING')){
    decision='DECLINE';
  }else if(reasons.length){
    decision='HOLD';
  }else if(o.canaryPassed && o.currentLease && o.receiptPath && net>=minMargin){
    decision='ADMIT_CURRENT';
  }

  const scoreDen=Math.max(1e-9,o.computeCost+o.bandwidthCost+o.settlementCost+o.coordinationCost+(o.energyMetricKnown?o.energyCost:0)+1);
  const marginalScore=(o.expectedUsefulValue+o.expectedRevenue)/scoreDen;

  const result={
    schema:'deus-compute-accord-decision/1',
    gateVersion:COMPUTE_ACCORD_GATE_VERSION,
    offer:o,
    decision,
    reasons,
    expectedNetValue:net,
    marginalScore,
    settlementReady:decision==='ADMIT_CURRENT' && (!o.paymentRequired||o.economicAuthority),
    supercellAttachAllowed:decision==='ADMIT_CURRENT' && (o.installMode==='NONE'||o.installConsent),
    truthBoundary:'DISCOVERY_NE_AUTHORITY__OFFER_NE_LEASE__LEASE_NE_EXECUTED__EXECUTED_NE_VERIFIED__MAPPED_DEVICE_NE_INSTALL_CONSENT',
  };
  return Object.freeze({...result,decisionDigest:digest(result)});
}

export function negotiateComputeAccord(offers=[],policy={}){
  if(!Array.isArray(offers)) throw new Error('offers must be an array');
  const decisions=offers.map(x=>evaluateComputeOffer(x,policy));
  const admitted=decisions.filter(x=>x.decision==='ADMIT_CURRENT').sort((a,b)=>b.marginalScore-a.marginalScore);
  return Object.freeze({
    schema:'deus-compute-accord-negotiation/1',
    gateVersion:COMPUTE_ACCORD_GATE_VERSION,
    counts:{
      total:decisions.length,
      admitted:admitted.length,
      candidate:decisions.filter(x=>x.decision==='OFFER_CANDIDATE').length,
      hold:decisions.filter(x=>x.decision==='HOLD').length,
      decline:decisions.filter(x=>x.decision==='DECLINE').length,
    },
    decisions,
    admitted,
    executionContract:'ONLY_ADMIT_CURRENT_MAY_ENTER_SUPERCELL_DISPATCH',
    settlementContract:'METER_ATTRIBUTABLE_USEFUL_RESULT_AND_ACTUAL_COST_BEFORE_SETTLEMENT_OR_REVENUE_SHARE',
    truthBoundary:'NO_COMMANDEERING__NO_UNKNOWN_DEVICE_INSTALL__NO_SPEND_WITHOUT_ECONOMIC_AUTHORITY__NO_SYNTHETIC_COMPUTE_OR_BANDWIDTH_CREDIT',
  });
}
