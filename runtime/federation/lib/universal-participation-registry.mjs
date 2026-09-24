import { createHash } from 'node:crypto';
import { projectInternetIdentityHierarchical } from './internet-functional-fabric.mjs';

export const PARTICIPATION_REGISTRY_VERSION='deus-universal-participation-registry/1.0';

const OFFER_ELIGIBLE_AUTHORITY=new Set([
  'OWNER_AUTHORIZED',
  'CONNECTED_ACCOUNT',
  'PUBLIC_SERVICE_INTENDED',
  'OPT_IN_MARKET',
  'OPT_IN_VOLUNTEER',
  'OPT_IN_SERVICE',
]);

function s(v,f=''){return v==null?f:String(v);}
function b(v){return v===true;}
function n(v,f=0){const x=Number(v);return Number.isFinite(x)?x:f;}
function digest(v){return createHash('sha256').update(JSON.stringify(v)).digest('hex');}

export function registerParticipationIdentity(raw={}){
  if(raw.value==null) throw new Error('value is required');
  const type=s(raw.type,'service').toLowerCase();
  const projection=projectInternetIdentityHierarchical({type,value:raw.value});
  const evidenceClass=s(raw.evidenceClass,'ADDRESS_ONLY').toUpperCase();
  const authorityClass=s(raw.authorityClass,'UNKNOWN').toUpperCase();
  const publicIntended=b(raw.publicIntended);
  const optIn=b(raw.optIn);
  const ownerAuthorized=b(raw.ownerAuthorized);
  const connectedAccount=authorityClass==='CONNECTED_ACCOUNT';
  const authorityEligible=OFFER_ELIGIBLE_AUTHORITY.has(authorityClass)
    && (publicIntended||optIn||ownerAuthorized||connectedAccount);
  const computeHint=b(raw.computeHint);
  const serviceHint=b(raw.serviceHint);
  const installConsent=b(raw.installConsent);

  let registrationClass='REGISTERED_OBSERVED';
  if(evidenceClass==='ADDRESS_ONLY'||evidenceClass==='UNKNOWN') registrationClass='REGISTERED_ADDRESS_ONLY';
  else if(evidenceClass==='DATA_ONLY') registrationClass='REGISTERED_DATA_ONLY';
  else if(serviceHint) registrationClass='REGISTERED_SERVICE';

  const participationClass=authorityEligible
    ? (computeHint?'OFFER_ELIGIBLE_COMPUTE':'OFFER_ELIGIBLE_SERVICE')
    : 'INDEX_ONLY';

  const core={
    schema:'deus-participation-registration/1',
    registryVersion:PARTICIPATION_REGISTRY_VERSION,
    type,
    value:projection.value,
    resourceKey:projection.resourceKey,
    supercellId:projection.supercellId,
    microcellId:projection.microcellId,
    locator:projection.locator,
    source:s(raw.source,'UNKNOWN_SOURCE'),
    sourceEvidenceRef:raw.sourceEvidenceRef==null?null:s(raw.sourceEvidenceRef),
    observedAt:raw.observedAt==null?null:s(raw.observedAt),
    evidenceClass,
    registrationClass,
    authorityClass,
    publicIntended,
    optIn,
    ownerAuthorized,
    installConsent,
    computeHint,
    serviceHint,
    participationClass,
    kernelIndexed:true,
    logicalActivationAllowed:true,
    offerEligible:authorityEligible,
    executionAdmitted:false,
    supercellComputeAttachAllowed:false,
    installAllowed:false,
    leaseState:'NONE',
    freshnessState:s(raw.freshnessState,'UNKNOWN').toUpperCase(),
    metadata:raw.metadata??{},
    truthBoundary:'REGISTERED_NE_AUTHORIZED__LOGICAL_ACTIVATION_NE_REMOTE_EXECUTION__ADDRESSABILITY_NE_DEVICE_EXISTENCE__MAPPED_DEVICE_NE_INSTALL_RIGHT',
  };
  return Object.freeze({...core,registrationDigest:digest(core)});
}

export function registerParticipationBatch(records=[]){
  if(!Array.isArray(records)) throw new Error('records must be an array');
  const byKey=new Map();
  for(const raw of records){
    const r=registerParticipationIdentity(raw);
    const previous=byKey.get(r.resourceKey);
    if(!previous) byKey.set(r.resourceKey,r);
    else {
      const preferred=(r.offerEligible&&!previous.offerEligible)?r:previous;
      byKey.set(r.resourceKey,preferred);
    }
  }
  const registrations=[...byKey.values()];
  const counts={total:registrations.length,indexOnly:0,offerEligible:0,executionAdmitted:0,addressOnly:0};
  for(const r of registrations){
    if(r.offerEligible) counts.offerEligible++; else counts.indexOnly++;
    if(r.executionAdmitted) counts.executionAdmitted++;
    if(r.registrationClass==='REGISTERED_ADDRESS_ONLY') counts.addressOnly++;
  }
  const payload={
    schema:'deus-participation-registry-batch/1',
    registryVersion:PARTICIPATION_REGISTRY_VERSION,
    counts,
    registrations,
    truthBoundary:'BATCH_REGISTRATION_IS_KERNEL_INDEXING__NOT_A_COMPUTE_GRANT_OR_INSTALL_PERMISSION',
  };
  return Object.freeze({...payload,batchDigest:digest({counts,keys:registrations.map(x=>x.resourceKey).sort()})});
}

export function promoteRegistrationWithAccord(registration,accordDecision={}){
  if(!registration?.resourceKey) throw new Error('registration is required');
  const decision=s(accordDecision.decision,'HOLD').toUpperCase();
  const admitted=decision==='ADMIT_CURRENT'
    && accordDecision.supercellAttachAllowed===true
    && registration.offerEligible===true;
  return Object.freeze({
    ...registration,
    participationClass:admitted?'EXECUTION_ADMITTED_CURRENT':registration.participationClass,
    executionAdmitted:admitted,
    supercellComputeAttachAllowed:admitted,
    installAllowed:admitted && registration.installConsent===true,
    leaseState:admitted?'ACTIVE':'NONE',
    accordDecisionDigest:accordDecision.decisionDigest??null,
    promotionTruthBoundary:'ACCORD_ADMISSION_IS_RUN_SCOPED__INSTALL_STILL_REQUIRES_EXPLICIT_CONSENT__LEASE_EXPIRY_REVOKES_EXECUTION',
  });
}

export function buildParticipationLease({
  registration,
  leaseId,
  issuedAt,
  expiresAt,
  heartbeatIntervalMs=30000,
  capacity={},
}={}){
  if(!registration?.executionAdmitted) throw new Error('execution-admitted registration required');
  if(!leaseId||!issuedAt||!expiresAt) throw new Error('leaseId, issuedAt, expiresAt are required');
  const issued=Date.parse(issuedAt),expires=Date.parse(expiresAt);
  if(!Number.isFinite(issued)||!Number.isFinite(expires)||expires<=issued) throw new Error('invalid lease interval');
  const core={
    schema:'deus-participation-lease/1',
    leaseId:s(leaseId),
    resourceKey:registration.resourceKey,
    issuedAt:new Date(issued).toISOString(),
    expiresAt:new Date(expires).toISOString(),
    heartbeatIntervalMs:Math.max(1000,Math.trunc(n(heartbeatIntervalMs,30000))),
    capacity,
    state:'ACTIVE',
    settlementState:'UNSETTLED',
    truthBoundary:'ACTIVE_LEASE_NE_PERMANENT_CAPACITY__EXPIRED_OR_REVOKED_LEASE_MUST_NOT_DISPATCH',
  };
  return Object.freeze({...core,leaseDigest:digest(core)});
}

export function leaseHealth(lease,{now=Date.now(),lastHeartbeatAt=null}={}){
  if(!lease?.leaseId) throw new Error('lease is required');
  const expires=Date.parse(lease.expiresAt);
  if(now>=expires) return Object.freeze({state:'EXPIRED',dispatchAllowed:false,reason:'LEASE_EXPIRED'});
  if(lastHeartbeatAt!=null){
    const hb=Date.parse(lastHeartbeatAt);
    const maxGap=n(lease.heartbeatIntervalMs,30000)*2;
    if(!Number.isFinite(hb)||now-hb>maxGap) return Object.freeze({state:'STALE',dispatchAllowed:false,reason:'HEARTBEAT_STALE'});
  }
  return Object.freeze({state:'ACTIVE',dispatchAllowed:true,reason:'LEASE_HEALTHY'});
}
