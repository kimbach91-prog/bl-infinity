import { sha256, sha256Json } from './canonical.mjs';
import { compileLogicalMicrocellShards, ONE_T_LOGICAL_NAMESPACE } from './logical-resource-compiler.mjs';

export const INTERNET_FUNCTIONAL_FABRIC_VERSION='deus-internet-functional-fabric/2.1';
export const CAPABILITY_ABI_VERSION='deus-capability-abi/2.0';
export const GENERATIVE_NAMESPACE_VERSION='deus-generative-namespace/1.0';
export const SUPERCELL_PROFILE='SCALE_FREE_HIERARCHICAL_SYNERGY_V2_PLUS_1T_NAMESPACE';
export const MAX_HOT_ROUTES_DEFAULT=64;

const DATA_RANK=new Map([['PUBLIC',0],['BL-S0',0],['S0',0],['BL-S1',1],['S1',1],['BL-S2',2],['S2',2],['BL-S3',3],['S3',3],['BL-S4',4],['S4',4]]);
const ROUTABLE_STATES=new Set(['ACTIVE','VERIFIED','AVAILABLE','EXECUTED_VERIFIED_SCOPED']);
const SIDE_EFFECTS=new Set(['READ_ONLY','TRANSFORM','EXECUTE','WRITE','UNKNOWN']);

function str(v,n){
  const x=String(v??'').trim();
  if(!x) throw new Error(n+' required');
  return x;
}
function num(v,n,fallback=0){
  const x=Number(v??fallback);
  if(!Number.isFinite(x)||x<0) throw new Error(n+' must be non-negative');
  return x;
}
function maybeNum(v,n){return v==null||v==='UNKNOWN'?null:num(v,n);}
function bool(v,fallback=false){return v==null?fallback:(v===true||String(v).toLowerCase()==='true');}
function clone(v){return v===undefined?undefined:structuredClone(v);}
function uniq(xs){return [...new Set((xs??[]).map(String).map(x=>x.trim()).filter(Boolean))];}
function dataRank(v){return DATA_RANK.get(String(v??'PUBLIC').toUpperCase())??99;}
function isoOrNull(v,n){
  if(v==null||v==='') return null;
  const s=String(v);
  if(!Number.isFinite(Date.parse(s))) throw new Error(n+' must be an ISO-compatible timestamp');
  return s;
}
function encodeSegment(v){return encodeURIComponent(String(v).trim());}
function namespacePrefix(template){
  const i=template.indexOf('{');
  return (i<0?template:template.slice(0,i)).replace(/\/+$/,'/');
}

export function internetNamespace(parts=[]){
  const segs=(Array.isArray(parts)?parts:[parts])
    .flatMap(x=>String(x??'').split('/')).map(x=>x.trim().toLowerCase()).filter(Boolean).map(encodeSegment);
  if(!segs.length) throw new Error('namespace parts required');
  return 'deus://internet/'+segs.join('/');
}

export function capabilityUri(id,inputType='ANY',outputType='ANY'){
  return `cap://${encodeSegment(id)}/${encodeSegment(inputType)}->${encodeSegment(outputType)}`;
}

function parseCapabilityUri(value){
  const body=String(value).slice('cap://'.length);
  const slash=body.indexOf('/');
  if(slash<1) throw new Error('invalid capability URI');
  const arrow=body.indexOf('->',slash+1);
  if(arrow<0) throw new Error('invalid capability URI');
  return {
    id:decodeURIComponent(body.slice(0,slash)),
    inputType:decodeURIComponent(body.slice(slash+1,arrow)),
    outputType:decodeURIComponent(body.slice(arrow+2)),
  };
}

export function normalizeCapabilitySignature(raw){
  const source=typeof raw==='string'
    ?(raw.startsWith('cap://')?parseCapabilityUri(raw):{id:raw})
    :(raw??{});
  const id=str(source.id??source.capability??source.name??source.verb,'capability.id');
  const inputType=String(source.inputType??source.input??'ANY').trim()||'ANY';
  const outputType=String(source.outputType??source.output??'ANY').trim()||'ANY';
  const sideEffect=String(source.sideEffect??'UNKNOWN').toUpperCase();
  if(!SIDE_EFFECTS.has(sideEffect)) throw new Error('invalid sideEffect for '+id);
  const receiptSchema=source.receiptSchema??source.receipt?.schema??null;
  const record={
    schema:CAPABILITY_ABI_VERSION,
    id,
    uri:capabilityUri(id,inputType,outputType),
    inputType,
    outputType,
    protocols:Object.freeze(uniq(source.protocols??[]).map(x=>x.toUpperCase())),
    sideEffect,
    deterministic:bool(source.deterministic,false),
    dataCeiling:source.dataCeiling==null?null:String(source.dataCeiling),
    receiptSchema:receiptSchema==null?null:String(receiptSchema),
    verifier:source.verifier==null?null:String(source.verifier),
    metadata:clone(source.metadata??{}),
  };
  return Object.freeze(record);
}

function normalizeFreshness(raw={}){
  return Object.freeze({
    observedAt:isoOrNull(raw.observedAt??raw.checkedAt??null,'freshness.observedAt'),
    expiresAt:isoOrNull(raw.expiresAt??null,'freshness.expiresAt'),
    ttlMs:maybeNum(raw.ttlMs,'freshness.ttlMs'),
    sourceFingerprint:raw.sourceFingerprint==null?null:String(raw.sourceFingerprint),
    evidenceRef:raw.evidenceRef==null?null:String(raw.evidenceRef),
  });
}

function normalizeQuota(raw={}){
  return Object.freeze({
    limit:maybeNum(raw.limit,'quota.limit'),
    remaining:maybeNum(raw.remaining,'quota.remaining'),
    resetAt:isoOrNull(raw.resetAt??null,'quota.resetAt'),
    unit:raw.unit==null?null:String(raw.unit),
  });
}

function normalizeReceipt(raw={}){
  return Object.freeze({
    capable:bool(raw.capable,raw.schema!=null),
    schema:raw.schema==null?null:String(raw.schema),
    verifier:raw.verifier==null?null:String(raw.verifier),
    lastReceiptRef:raw.lastReceiptRef==null?null:String(raw.lastReceiptRef),
  });
}

export function normalizeInternetResource(raw={}){
  const id=str(raw.id,'resource.id');
  const namespace=str(raw.namespace??internetNamespace([raw.family??'resource',id]),'resource.namespace');
  if(!namespace.startsWith('deus://internet/')) throw new Error('resource namespace must use deus://internet/');
  const abiSource=raw.capabilityAbi??raw.capabilities??[];
  if(!Array.isArray(abiSource)||abiSource.length===0) throw new Error('resource '+id+' capabilities required');
  const capabilityAbi=abiSource.map(normalizeCapabilitySignature);
  const capabilityIds=capabilityAbi.map(x=>x.id);
  if(new Set(capabilityIds).size!==capabilityIds.length) throw new Error('duplicate capability id on resource '+id);
  const allowedDataClasses=uniq(raw.authorization?.allowedDataClasses??['PUBLIC']);
  const expiresAt=isoOrNull(raw.authorization?.expiresAt??null,'authorization.expiresAt');
  return Object.freeze({
    id,
    namespace,
    family:String(raw.family??'GENERIC').toUpperCase(),
    provider:String(raw.provider??'UNKNOWN'),
    endpoint:raw.endpoint==null?null:String(raw.endpoint),
    protocols:Object.freeze(uniq(raw.protocols??[]).map(x=>x.toUpperCase())),
    capabilities:Object.freeze(capabilityIds),
    capabilityAbi:Object.freeze(capabilityAbi),
    authorization:Object.freeze({
      mode:String(raw.authorization?.mode??'PUBLIC').toUpperCase(),
      standing:raw.authorization?.standing!==false,
      allowedDataClasses:Object.freeze(allowedDataClasses),
      authorityScope:raw.authorization?.authorityScope==null?null:String(raw.authorization.authorityScope),
      expiresAt,
    }),
    telemetry:Object.freeze({
      trust:Math.min(1,num(raw.telemetry?.trust,'telemetry.trust',0.5)),
      availability:Math.min(1,num(raw.telemetry?.availability,'telemetry.availability',1)),
      p95LatencyMs:maybeNum(raw.telemetry?.p95LatencyMs,'telemetry.p95LatencyMs'),
      estimatedBandwidthMbps:maybeNum(raw.telemetry?.estimatedBandwidthMbps,'telemetry.estimatedBandwidthMbps'),
      costPerUnitUsd:num(raw.telemetry?.costPerUnitUsd,'telemetry.costPerUnitUsd',0),
      coordinationMs:num(raw.telemetry?.coordinationMs,'telemetry.coordinationMs',0),
    }),
    freshness:normalizeFreshness(raw.freshness??{}),
    quota:normalizeQuota(raw.quota??{}),
    receipt:normalizeReceipt(raw.receipt??{}),
    rateLimit:clone(raw.rateLimit??null),
    cache:clone(raw.cache??null),
    locality:clone(raw.locality??null),
    fallbacks:Object.freeze(uniq(raw.fallbacks??[])),
    dedupGroup:String(raw.dedupGroup??id),
    independenceGroup:String(raw.independenceGroup??raw.provider??id),
    state:String(raw.state??'ACTIVE').toUpperCase(),
    sourceRef:raw.sourceRef==null?null:String(raw.sourceRef),
    metadata:clone(raw.metadata??{}),
  });
}

export function compileCapabilityAtlas(resources=[]){
  if(!Array.isArray(resources)) throw new Error('resources must be an array');
  const normalized=resources.map(normalizeInternetResource);
  const ids=new Set();
  const namespaces=new Set();
  for(const r of normalized){
    if(ids.has(r.id)) throw new Error('duplicate resource id '+r.id);
    if(namespaces.has(r.namespace)) throw new Error('duplicate resource namespace '+r.namespace);
    ids.add(r.id);namespaces.add(r.namespace);
  }
  const payload={
    schema:INTERNET_FUNCTIONAL_FABRIC_VERSION,
    capabilityAbiSchema:CAPABILITY_ABI_VERSION,
    resources:normalized,
    summary:{
      resources:normalized.length,
      providers:new Set(normalized.map(x=>x.provider)).size,
      families:new Set(normalized.map(x=>x.family)).size,
      capabilityCount:new Set(normalized.flatMap(x=>x.capabilities)).size,
      receiptCapable:normalized.filter(x=>x.receipt.capable||x.capabilityAbi.some(c=>c.receiptSchema)).length,
      freshnessObserved:normalized.filter(x=>x.freshness.observedAt).length,
    },
    truthBoundary:'ATLAS_KNOWLEDGE_NE_EXECUTION_AUTHORITY__PUBLIC_NE_UNLIMITED__NAMESPACE_NE_PHYSICAL_WORKER__SCHEMA_NE_RECEIPT',
  };
  return Object.freeze({...payload,atlasDigest:sha256Json(payload)});
}

function normalizeNamespaceFamily(raw,index){
  const id=str(raw.id??`family-${index+1}`,'namespaceFamily.id');
  const template=str(raw.template??raw.namespaceTemplate,'namespaceFamily.template');
  if(!template.startsWith('deus://internet/')) throw new Error('namespace family template must use deus://internet/');
  const estimatedCardinality=raw.estimatedCardinality==null?null:String(raw.estimatedCardinality);
  if(estimatedCardinality!=null){
    try{if(BigInt(estimatedCardinality)<0n) throw new Error();}
    catch{throw new Error('estimatedCardinality must be a non-negative integer');}
  }
  const capabilityAbi=(raw.capabilityAbi??raw.capabilities??[]).map(normalizeCapabilitySignature);
  return Object.freeze({
    id,
    template,
    prefix:namespacePrefix(template),
    capabilityAbi:Object.freeze(capabilityAbi),
    capabilities:Object.freeze(capabilityAbi.map(x=>x.id)),
    estimatedCardinality,
    authority:String(raw.authority??'RESOURCE_BOUND'),
    materializer:String(raw.materializer??'ATLAS_PREFIX_LAZY'),
    maxMaterialized:Math.max(1,Math.trunc(num(raw.maxMaterialized,'namespaceFamily.maxMaterialized',64))),
    sourceRef:raw.sourceRef==null?null:String(raw.sourceRef),
    freshness:normalizeFreshness(raw.freshness??{}),
    metadata:clone(raw.metadata??{}),
  });
}

export function compileGenerativeNamespace(families=[]){
  if(!Array.isArray(families)) throw new Error('namespace families must be an array');
  const normalized=families.map(normalizeNamespaceFamily);
  if(new Set(normalized.map(x=>x.id)).size!==normalized.length) throw new Error('namespace family ids must be unique');
  const payload={
    schema:GENERATIVE_NAMESPACE_VERSION,
    families:normalized,
    summary:{
      families:normalized.length,
      declaredCardinality:normalized.reduce((a,x)=>a+(x.estimatedCardinality==null?0n:BigInt(x.estimatedCardinality)),0n).toString(),
      materialized:0,
    },
    truthBoundary:'DECLARED_LOGICAL_CARDINALITY_NE_MATERIALIZED_OBJECTS__RESOLUTION_IS_PREFIX_AND_CAPABILITY_BOUND__IDENTITY_NE_AUTHORITY',
  };
  return Object.freeze({...payload,namespaceDigest:sha256Json(payload)});
}

function hierarchicalCapabilityMatch(provided,required){
  return provided===required||provided.startsWith(required+'.')||required.startsWith(provided+'.');
}
function typeCompatible(provided,required){
  return required==='ANY'||required==='*'||provided==='ANY'||provided==='*'||provided===required;
}
function matchedCapability(resource,required){
  return resource.capabilityAbi.find(c=>
    hierarchicalCapabilityMatch(c.id,required.id)&&
    typeCompatible(c.inputType,required.inputType)&&
    typeCompatible(c.outputType,required.outputType)&&
    (required.sideEffect==='UNKNOWN'||c.sideEffect==='UNKNOWN'||c.sideEffect===required.sideEffect)&&
    (required.protocols.length===0||required.protocols.some(p=>c.protocols.includes(p)||resource.protocols.includes(p)))
  )??null;
}
function authorizedFor(resource,dataClass,now){
  if(resource.authorization.standing!==true) return false;
  if(resource.authorization.expiresAt&&Date.parse(resource.authorization.expiresAt)<=now) return false;
  const need=dataRank(dataClass);
  return resource.authorization.allowedDataClasses.some(x=>dataRank(x)>=need);
}
function freshnessState(resource,now,maxEvidenceAgeMs){
  const f=resource.freshness;
  if(f.expiresAt&&Date.parse(f.expiresAt)<=now) return 'STALE';
  if(f.observedAt&&f.ttlMs!=null&&Date.parse(f.observedAt)+f.ttlMs<=now) return 'STALE';
  if(maxEvidenceAgeMs!=null){
    if(!f.observedAt) return 'UNKNOWN_BLOCKED';
    if(Date.parse(f.observedAt)+maxEvidenceAgeMs<=now) return 'STALE';
  }
  return f.observedAt?'FRESH':'UNKNOWN';
}
function quotaAvailable(resource,now,requireKnownQuota){
  const q=resource.quota;
  if(q.resetAt&&Date.parse(q.resetAt)<=now) return !requireKnownQuota;
  if(q.remaining==null) return !requireKnownQuota;
  return q.remaining>0;
}
function receiptCompatible(resource,capability,required){
  const schemas=uniq([resource.receipt.schema,capability?.receiptSchema].filter(Boolean));
  const capable=resource.receipt.capable===true||schemas.length>0;
  if(!capable) return false;
  return required.receiptSchema==null||schemas.includes(required.receiptSchema);
}
function namespaceMatches(resource,query,index,requiredCapability){
  const requested=String(query??'deus://internet/');
  if(!requested.startsWith('deus://internet/')) throw new Error('namespace query must use deus://internet/');
  if(!resource.namespace.startsWith(requested)) return false;
  if(!index||index.families.length===0) return true;
  return index.families.some(f=>
    (resource.namespace.startsWith(f.prefix)||requested.startsWith(f.prefix)||f.prefix.startsWith(requested))&&
    (f.capabilities.length===0||f.capabilities.some(c=>hierarchicalCapabilityMatch(c,requiredCapability.id)))
  );
}
function normalizeRouteUtilityMemory(raw){
  if(raw==null) return Object.freeze([]);
  const entries=Array.isArray(raw)
    ?raw
    :Object.entries(raw).map(([resourceId,value])=>({...(value??{}),resourceId:value?.resourceId??resourceId}));
  return Object.freeze(entries.map((item,index)=>{
    const row=item??{};
    const observedAt=isoOrNull(row.observedAt??null,'routeUtilityMemory['+index+'].observedAt');
    const ttlMs=maybeNum(row.ttlMs,'routeUtilityMemory['+index+'].ttlMs');
    return Object.freeze({
      resourceId:row.resourceId==null?null:String(row.resourceId),
      provider:row.provider==null?null:String(row.provider),
      taskFamily:row.taskFamily==null?null:String(row.taskFamily),
      queryFingerprint:row.queryFingerprint==null?null:String(row.queryFingerprint),
      quality:row.quality==null?null:Math.min(1,num(row.quality,'routeUtilityMemory['+index+'].quality')),
      successCount:Math.trunc(num(row.successCount,'routeUtilityMemory['+index+'].successCount',0)),
      failureCount:Math.trunc(num(row.failureCount,'routeUtilityMemory['+index+'].failureCount',0)),
      reuseCount:Math.trunc(num(row.reuseCount,'routeUtilityMemory['+index+'].reuseCount',0)),
      scarCount:Math.trunc(num(row.scarCount,'routeUtilityMemory['+index+'].scarCount',0)),
      observedAt,
      ttlMs,
      sourceRef:row.sourceRef==null?null:String(row.sourceRef),
    });
  }));
}
function routeUtilityPrior(resource,records,{taskFamily=null,queryFingerprint=null,now=Date.now()}={}){
  const task=taskFamily==null?null:String(taskFamily);
  const query=queryFingerprint==null?null:String(queryFingerprint);
  const eligible=records.filter(r=>{
    if(r.resourceId!=null&&r.resourceId!==resource.id) return false;
    if(r.provider!=null&&r.provider!==resource.provider) return false;
    if(r.taskFamily!=null&&task!=null&&r.taskFamily!==task) return false;
    if(r.queryFingerprint!=null&&query!=null&&r.queryFingerprint!==query) return false;
    if(r.taskFamily!=null&&task==null) return false;
    if(r.queryFingerprint!=null&&query==null) return false;
    if(r.observedAt&&r.ttlMs!=null&&Date.parse(r.observedAt)+r.ttlMs<=now) return false;
    return true;
  }).sort((a,b)=>{
    const specificity=x=>(x.resourceId!=null?4:0)+(x.provider!=null?2:0)+(x.taskFamily!=null?1:0)+(x.queryFingerprint!=null?1:0);
    const d=specificity(b)-specificity(a);
    if(d!==0) return d;
    return (b.observedAt?Date.parse(b.observedAt):0)-(a.observedAt?Date.parse(a.observedAt):0);
  });
  const row=eligible[0];
  if(!row) return Object.freeze({applied:false,multiplier:1,confidence:0,empiricalSuccess:null,quality:null,reuseCount:0,scarCount:0,sourceRef:null});
  const total=row.successCount+row.failureCount;
  const empiricalSuccess=(row.successCount+1)/(total+2);
  const quality=row.quality??empiricalSuccess;
  const confidence=total===0?0:Math.min(1,Math.log2(1+total)/5);
  const learnedSignal=empiricalSuccess*quality;
  const reuseBonus=Math.min(0.12,Math.log1p(row.reuseCount)*0.03);
  const scarPenalty=Math.min(0.25,row.scarCount*0.05);
  const rawMultiplier=1+confidence*(learnedSignal-0.5)*0.8+reuseBonus-scarPenalty;
  const multiplier=Math.max(0.6,Math.min(1.4,rawMultiplier));
  return Object.freeze({
    applied:true,multiplier,confidence,empiricalSuccess,quality,
    reuseCount:row.reuseCount,scarCount:row.scarCount,sourceRef:row.sourceRef,
    observedAt:row.observedAt,ttlMs:row.ttlMs,
    taskFamily:row.taskFamily,queryFingerprint:row.queryFingerprint,
  });
}
function routeMetrics(resource,capability,required,freshness,requireReceipt,utilityPrior=null){
  const freshnessFactor=freshness==='FRESH'?1:(freshness==='UNKNOWN'?0.7:0);
  const posteriorUseful=resource.telemetry.trust*resource.telemetry.availability*freshnessFactor;
  const latency=resource.telemetry.p95LatencyMs??1000;
  const bandwidth=resource.telemetry.estimatedBandwidthMbps??0;
  const rawCacheHit=Number(resource.cache?.hitProbability??0);
  const cacheHit=Number.isFinite(rawCacheHit)?Math.max(0,Math.min(1,rawCacheHit)):0;
  const receiptFactor=requireReceipt?(receiptCompatible(resource,capability,required)?1:0):1;
  const expectedVerifiedUsefulResult=posteriorUseful*receiptFactor*(1+Math.min(1,Math.log10(1+bandwidth)/4))*(1+cacheHit*0.25);
  const coordination=(latency+resource.telemetry.coordinationMs)/1000;
  const costPenalty=resource.telemetry.costPerUnitUsd*1000;
  const denominator=1+coordination+costPenalty;
  const baseMarginalValue=expectedVerifiedUsefulResult/denominator;
  const prior=utilityPrior??Object.freeze({applied:false,multiplier:1,confidence:0});
  return Object.freeze({
    posteriorUseful,
    expectedVerifiedUsefulResult,
    baseMarginalValue,
    marginalValue:baseMarginalValue*prior.multiplier,
    freshness,
    latencyMs:latency,
    costPerUnitUsd:resource.telemetry.costPerUnitUsd,
    cacheHitProbability:cacheHit,
    receiptCapable:receiptCompatible(resource,capability,required),
    utilityPrior:prior,
  });
}

export function evaluateTaskFitRoutes(atlas,{
  capability,operatorAbi=null,dataClass='BL-S0',namespace='deus://internet/',namespaceIndex=null,
  maxRoutes=8,now=Date.now(),requireIndependent=false,requireReceipt=false,
  maxEvidenceAgeMs=null,minTrust=0,maxCostPerUnitUsd=null,requireKnownQuota=false,
  routeUtilityMemory=null,utilityTaskFamily=null,utilityQueryFingerprint=null,
}={}){
  const required=normalizeCapabilitySignature(operatorAbi??capability);
  const evidenceAge=maxEvidenceAgeMs==null?null:num(maxEvidenceAgeMs,'maxEvidenceAgeMs');
  const minimumTrust=Math.min(1,num(minTrust,'minTrust',0));
  const costCeiling=maxCostPerUnitUsd==null?null:num(maxCostPerUnitUsd,'maxCostPerUnitUsd');
  const utilityRecords=normalizeRouteUtilityMemory(routeUtilityMemory);
  const requestedLimit=Math.max(1,Math.trunc(num(maxRoutes,'maxRoutes',8)));
  const matchedNamespaceFamilies=(namespaceIndex?.families??[])
    .filter(f=>String(namespace).startsWith(f.prefix)||f.prefix.startsWith(String(namespace)))
    .filter(f=>f.capabilities.length===0||f.capabilities.some(c=>hierarchicalCapabilityMatch(c,required.id)));
  const familyLimit=matchedNamespaceFamilies.length
    ?Math.max(...matchedNamespaceFamilies.map(f=>f.maxMaterialized))
    :requestedLimit;
  const limit=Math.min(requestedLimit,familyLimit);
  const rejectionCounts={};
  const reject=(reason)=>{rejectionCounts[reason]=(rejectionCounts[reason]??0)+1;};
  const candidates=[];
  for(const resource of atlas.resources){
    if(!ROUTABLE_STATES.has(resource.state)){reject('STATE');continue;}
    if(!namespaceMatches(resource,namespace,namespaceIndex,required)){reject('NAMESPACE');continue;}
    const matched=matchedCapability(resource,required);
    if(!matched){reject('CAPABILITY_ABI');continue;}
    if(!authorizedFor(resource,dataClass,now)){reject('AUTHORITY');continue;}
    if(matched.dataCeiling!=null&&dataRank(matched.dataCeiling)<dataRank(dataClass)){reject('DATA_CEILING');continue;}
    const freshness=freshnessState(resource,now,evidenceAge);
    if(freshness==='STALE'||freshness==='UNKNOWN_BLOCKED'){reject('FRESHNESS');continue;}
    if(!quotaAvailable(resource,now,requireKnownQuota)){reject('QUOTA');continue;}
    if(resource.telemetry.trust<minimumTrust){reject('TRUST');continue;}
    if(costCeiling!=null&&resource.telemetry.costPerUnitUsd>costCeiling){reject('COST');continue;}
    if(requireReceipt&&!receiptCompatible(resource,matched,required)){reject('RECEIPT_PATH');continue;}
    const utilityPrior=routeUtilityPrior(resource,utilityRecords,{
      taskFamily:utilityTaskFamily,queryFingerprint:utilityQueryFingerprint,now,
    });
    const metrics=routeMetrics(resource,matched,required,freshness,requireReceipt,utilityPrior);
    candidates.push({resource,matched,metrics});
  }
  candidates.sort((a,b)=>b.metrics.marginalValue-a.metrics.marginalValue||a.resource.id.localeCompare(b.resource.id));
  const usedDedup=new Set();
  const usedIndependent=new Set();
  const routes=[];
  for(const item of candidates){
    const r=item.resource;
    if(usedDedup.has(r.dedupGroup)){reject('DEDUP');continue;}
    if(requireIndependent&&usedIndependent.has(r.independenceGroup)){reject('INDEPENDENCE');continue;}
    routes.push(Object.freeze({...r,matchedCapability:item.matched,selectionMetrics:item.metrics,selectionScore:item.metrics.marginalValue}));
    usedDedup.add(r.dedupGroup);
    usedIndependent.add(r.independenceGroup);
    if(routes.length>=limit) break;
  }
  const matchedFamilies=matchedNamespaceFamilies.map(f=>f.id);
  const payload={
    operatorAbi:required,
    namespace:String(namespace),
    matchedFamilyIds:Object.freeze(matchedFamilies),
    routes:Object.freeze(routes),
    rejectionCounts:Object.freeze(rejectionCounts),
    evaluatedResources:atlas.resources.length,
    materializedRoutes:routes.length,
    utilityPriorRoutes:routes.filter(x=>x.selectionMetrics.utilityPrior.applied).length,
    truthBoundary:'ROUTE_SELECTED_NE_ROUTE_EXECUTED__UTILITY_PRIOR_NE_AUTHORITY_OR_EXECUTION__POSTERIOR_AND_MARGINAL_VALUE_ARE_TASK_SELECTION_METRICS__PHYSICAL_CREDIT_REQUIRES_RECEIPT',
  };
  return Object.freeze({...payload,selectionDigest:sha256Json(payload)});
}

export function selectTaskFitRoutes(atlas,options={}){
  return evaluateTaskFitRoutes(atlas,options).routes;
}

export function resolveNamespaceCandidates(namespaceIndex,atlas,{
  namespace='deus://internet/',capability,maxResults=8,dataClass='BL-S0',now=Date.now(),
}={}){
  const evaluated=evaluateTaskFitRoutes(atlas,{
    capability,namespace,namespaceIndex,maxRoutes:maxResults,dataClass,now,
  });
  const payload={
    schema:GENERATIVE_NAMESPACE_RESOLUTION_SCHEMA,
    namespace,
    capability:evaluated.operatorAbi,
    matchedFamilyIds:evaluated.matchedFamilyIds,
    resourceIds:evaluated.routes.map(x=>x.id),
    materialized:evaluated.routes.length,
    logicalCardinality:namespaceIndex.summary.declaredCardinality,
    namespaceDigest:namespaceIndex.namespaceDigest,
    truthBoundary:'LOGICAL_CARDINALITY_NE_MATERIALIZED_ROUTES__RESOLUTION_NE_EXECUTION',
  };
  return Object.freeze({...payload,resolutionDigest:sha256Json(payload)});
}

const GENERATIVE_NAMESPACE_RESOLUTION_SCHEMA='deus-generative-namespace-resolution/1.0';

function defaultNamespaceFamilies(resources,logicalNamespace,maxHotRoutes){
  return [{
    id:'internet-root',
    template:'deus://internet/{layer}/{provider}/{service}/{capability}/{region}/{lane}',
    capabilityAbi:uniq(resources.flatMap(r=>r.capabilities??[])),
    estimatedCardinality:String(logicalNamespace),
    authority:'RESOURCE_BOUND',
    materializer:'ATLAS_PREFIX_LAZY',
    maxMaterialized:maxHotRoutes,
    sourceRef:'runtime atlas',
  }];
}

export function compileInternetFabricPlan({
  taskId,logicalUnits,resourceVector,resources,operators,namespaceFamilies=null,
  logicalNamespace=ONE_T_LOGICAL_NAMESPACE,maxHotRoutes=MAX_HOT_ROUTES_DEFAULT,
  maxPhysicalShards=64,dataClass='BL-S0',now=Date.now(),metadata={},
}={}){
  const id=str(taskId,'taskId');
  if(!Array.isArray(operators)||operators.length===0) throw new Error('operators must be non-empty');
  const atlas=compileCapabilityAtlas(resources??[]);
  const hotLimit=Math.max(1,Math.trunc(num(maxHotRoutes,'maxHotRoutes',MAX_HOT_ROUTES_DEFAULT)));
  const namespaceIndex=compileGenerativeNamespace(
    namespaceFamilies??defaultNamespaceFamilies(atlas.resources,logicalNamespace,hotLimit)
  );
  const shardPlan=compileLogicalMicrocellShards({
    taskId:id,logicalUnits,logicalNamespace,resourceVector,maxPhysicalShards,
    metadata:{profile:SUPERCELL_PROFILE},
  });
  const opIds=new Set();
  const selectedIds=new Set();
  const compiledOperators=[];
  for(let index=0;index<operators.length;index++){
    const op=operators[index];
    const opId=str(op.id??('op-'+(index+1)),'operator.id');
    if(opIds.has(opId)) throw new Error('duplicate operator id '+opId);
    opIds.add(opId);
    const deps=uniq(op.deps??[]);
    const operatorAbi=normalizeCapabilitySignature(op.operatorAbi??op.capability);
    const evaluation=evaluateTaskFitRoutes(atlas,{
      operatorAbi,
      dataClass:op.dataClass??dataClass,
      namespace:op.namespace??'deus://internet/',
      namespaceIndex,
      maxRoutes:Math.min(hotLimit,op.maxRoutes??hotLimit),
      now,
      requireIndependent:op.requireIndependent===true,
      requireReceipt:op.requireReceipt===true,
      maxEvidenceAgeMs:op.maxEvidenceAgeMs??null,
      minTrust:op.minTrust??0,
      maxCostPerUnitUsd:op.maxCostPerUnitUsd??null,
      requireKnownQuota:op.requireKnownQuota===true,
    });
    const boundedRoutes=[];
    let hotBudgetRejected=0;
    for(const route of evaluation.routes){
      if(selectedIds.has(route.id)){boundedRoutes.push(route);continue;}
      if(selectedIds.size>=hotLimit){hotBudgetRejected++;continue;}
      selectedIds.add(route.id);boundedRoutes.push(route);
    }
    const rejectionCounts={...evaluation.rejectionCounts};
    if(hotBudgetRejected) rejectionCounts.HOT_ROUTE_BUDGET=(rejectionCounts.HOT_ROUTE_BUDGET??0)+hotBudgetRejected;
    compiledOperators.push(Object.freeze({
      id:opId,
      capability:operatorAbi.id,
      operatorAbi,
      namespace:op.namespace??'deus://internet/',
      deps:Object.freeze(deps),
      logicalWorkUnits:op.logicalWorkUnits==null?null:String(op.logicalWorkUnits),
      state:boundedRoutes.length?'ROUTABLE':'HOLD_NO_ELIGIBLE_ROUTE',
      routes:Object.freeze(boundedRoutes),
      routeSelection:Object.freeze({
        selectionDigest:evaluation.selectionDigest,
        matchedFamilyIds:evaluation.matchedFamilyIds,
        evaluatedResources:evaluation.evaluatedResources,
        materializedRoutes:boundedRoutes.length,
        rejectionCounts:Object.freeze(rejectionCounts),
      }),
      fallbackPolicy:String(op.fallbackPolicy??'ALTERNATE_ROUTE_THEN_CHECKPOINT'),
      metadata:clone(op.metadata??{}),
    }));
  }
  for(const op of compiledOperators) for(const dep of op.deps) if(!opIds.has(dep)) throw new Error('unknown operator dependency '+dep);
  const selectedResourceIds=Object.freeze([...selectedIds]);
  const payload={
    schema:INTERNET_FUNCTIONAL_FABRIC_VERSION,
    profile:SUPERCELL_PROFILE,
    taskId:id,
    dataClass:String(dataClass),
    logicalNamespace:String(logicalNamespace),
    logicalUnits:String(logicalUnits),
    atlasDigest:atlas.atlasDigest,
    atlasSummary:atlas.summary,
    namespaceDigest:namespaceIndex.namespaceDigest,
    namespaceSummary:{...namespaceIndex.summary,materialized:selectedResourceIds.length},
    shardPlan,
    operators:Object.freeze(compiledOperators),
    selectedResourceIds,
    summary:{
      operators:compiledOperators.length,
      routableOperators:compiledOperators.filter(x=>x.state==='ROUTABLE').length,
      heldOperators:compiledOperators.filter(x=>x.state!=='ROUTABLE').length,
      physicalShards:shardPlan.physicalShards,
      addressableLogicalUnits:String(logicalUnits),
      hotRoutes:selectedResourceIds.length,
      maxHotRoutes:hotLimit,
    },
    metadata:clone(metadata),
    truthBoundary:'ONE_T_IS_LOGICAL_ADDRESS_SPACE__ONLY_BOUNDED_TASK_FIT_ROUTES_MATERIALIZE__ROUTE_FOUND_NE_ROUTE_LIVE__EACH_EXTERNAL_EFFECT_REQUIRES_ITS_OWN_AUTHORITY_AND_RECEIPT__NO_BLIND_SCANNING',
  };
  return Object.freeze({...payload,planDigest:sha256Json(payload)});
}

export function buildCrossCheckSet(atlas,{capability,dataClass='BL-S0',width=3,now=Date.now(),...rest}={}){
  return selectTaskFitRoutes(atlas,{capability,dataClass,maxRoutes:width,now,requireIndependent:true,...rest});
}


export const INTERNET_OBSERVATORY_KERNEL_VERSION='deus-internet-observatory-kernel/1.0';
export const INTERNET_ADDRESS_SLOT_DOMAIN=1000000000000n;
export const INTERNET_GENERATIVE_ADDRESS_FABRIC_VERSION='deus-internet-generative-address-fabric/2.0';
export const INTERNET_MICROCELL_BITS=64n;
export const INTERNET_MICROCELL_DOMAIN=1n<<INTERNET_MICROCELL_BITS;

function normalizeIdentityType(value){
  const type=String(value??'').trim().toLowerCase();
  if(!['ipv4','ipv6','cidr','dns','hostname','url','asn','service','protocol','provider','compute','generic'].includes(type)) throw new Error('unsupported identity type '+type);
  return type;
}
function parseIpv4(value){
  const parts=String(value).trim().split('.');
  if(parts.length!==4) throw new Error('invalid IPv4 address');
  let out=0n;
  for(const part of parts){
    if(!/^\d{1,3}$/.test(part)) throw new Error('invalid IPv4 address');
    const n=Number(part);
    if(n<0||n>255) throw new Error('invalid IPv4 address');
    out=(out<<8n)|BigInt(n);
  }
  return out;
}
function formatIpv4(value){
  if(value<0n||value>0xffffffffn) throw new Error('IPv4 integer out of range');
  return [24n,16n,8n,0n].map(shift=>Number((value>>shift)&255n)).join('.');
}
function ipv4TailToGroups(value){
  const n=parseIpv4(value);
  return [Number((n>>16n)&0xffffn).toString(16),Number(n&0xffffn).toString(16)];
}
function parseIpv6(value){
  let text=String(value).trim().toLowerCase();
  const zone=text.indexOf('%');
  if(zone>=0) text=text.slice(0,zone);
  if(text.includes('.')){
    const lastColon=text.lastIndexOf(':');
    if(lastColon<0) throw new Error('invalid IPv6 address');
    const tail=ipv4TailToGroups(text.slice(lastColon+1));
    text=text.slice(0,lastColon+1)+tail.join(':');
  }
  const pieces=text.split('::');
  if(pieces.length>2) throw new Error('invalid IPv6 address');
  const left=pieces[0]?pieces[0].split(':'):[];
  const right=pieces.length===2&&pieces[1]?pieces[1].split(':'):[];
  const missing=8-left.length-right.length;
  if((pieces.length===1&&missing!==0)||(pieces.length===2&&missing<1)) throw new Error('invalid IPv6 address');
  const groups=[...left,...Array(missing).fill('0'),...right];
  if(groups.length!==8) throw new Error('invalid IPv6 address');
  let out=0n;
  for(const group of groups){
    if(!/^[0-9a-f]{1,4}$/.test(group)) throw new Error('invalid IPv6 address');
    out=(out<<16n)|BigInt('0x'+group);
  }
  return out;
}
function formatIpv6(value){
  if(value<0n||value>((1n<<128n)-1n)) throw new Error('IPv6 integer out of range');
  const groups=[];
  for(let i=0;i<8;i++) groups.push(Number((value>>BigInt((7-i)*16))&0xffffn).toString(16));
  let bestStart=-1,bestLen=0;
  for(let i=0;i<8;){
    if(groups[i]!=='0'){i++;continue;}
    let j=i;
    while(j<8&&groups[j]==='0') j++;
    if(j-i>bestLen&&j-i>=2){bestStart=i;bestLen=j-i;}
    i=j;
  }
  if(bestStart<0) return groups.join(':');
  const left=groups.slice(0,bestStart).join(':');
  const right=groups.slice(bestStart+bestLen).join(':');
  return (left?left:'')+'::'+(right?right:'');
}
function parseCidr(value){
  const text=String(value).trim();
  const slash=text.lastIndexOf('/');
  if(slash<1) throw new Error('CIDR prefix required');
  const addr=text.slice(0,slash);
  const prefix=Number(text.slice(slash+1));
  const family=addr.includes(':')?'ipv6':'ipv4';
  const bits=family==='ipv6'?128:32;
  if(!Number.isInteger(prefix)||prefix<0||prefix>bits) throw new Error('invalid CIDR prefix');
  const parsed=family==='ipv6'?parseIpv6(addr):parseIpv4(addr);
  const hostBits=bits-prefix;
  const all=(1n<<BigInt(bits))-1n;
  const hostMask=hostBits===0?0n:(1n<<BigInt(hostBits))-1n;
  const network=parsed&(all^hostMask);
  return {family,bits,prefix,network,hostBits,canonical:(family==='ipv6'?formatIpv6(network):formatIpv4(network))+'/'+prefix};
}
function canonicalizeUrl(value){
  const u=new URL(String(value).trim());
  u.hostname=u.hostname.toLowerCase();
  return u.toString();
}

export function canonicalizeInternetIdentity(raw={}){
  const type=normalizeIdentityType(raw.type??raw.kind);
  let value=String(raw.value??raw.address??raw.id??'').trim();
  if(!value) throw new Error('identity value required');
  if(type==='ipv4') value=formatIpv4(parseIpv4(value));
  else if(type==='ipv6') value=formatIpv6(parseIpv6(value));
  else if(type==='cidr') value=parseCidr(value).canonical;
  else if(type==='dns'||type==='hostname') value=value.toLowerCase().replace(/\.+$/,'');
  else if(type==='url') value=canonicalizeUrl(value);
  else if(type==='asn'){
    const match=value.toUpperCase().match(/^(?:AS)?(\d+)$/);
    if(!match) throw new Error('invalid ASN');
    value='AS'+BigInt(match[1]).toString();
  } else value=value.toLowerCase();
  return Object.freeze({type,value});
}

export function projectInternetIdentity(raw,{slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN}={}){
  const identity=canonicalizeInternetIdentity(raw);
  const domain=BigInt(slotDomain);
  if(domain<=0n) throw new Error('slotDomain must be positive');
  const resourceKey=sha256(identity.type+'|'+identity.value);
  const slotId=(BigInt('0x'+resourceKey)%domain).toString();
  return Object.freeze({
    schema:'deus-internet-resource-projection/1',
    ...identity,
    resourceKey,
    slotId,
    slotDomain:domain.toString(),
    namespace:'deus://internet/address/'+identity.type+'/'+encodeSegment(identity.value),
    truthBoundary:'PROJECTED_IDENTITY_NE_OBSERVED_LIVE_SERVICE_NE_EXECUTION_AUTHORITY',
  });
}


function resourceKeyInteger(resourceKey){
  const value=String(resourceKey??'').toLowerCase();
  if(!/^[0-9a-f]{64}$/.test(value)) throw new Error('resourceKey must be a 256-bit lowercase hex digest');
  return BigInt('0x'+value);
}

export function projectInternetIdentityHierarchical(raw,{
  slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN,
  microcellDomain=INTERNET_MICROCELL_DOMAIN,
}={}){
  const slots=BigInt(slotDomain);
  const microcells=BigInt(microcellDomain);
  if(slots<=0n) throw new Error('slotDomain must be positive');
  if(microcells<=0n) throw new Error('microcellDomain must be positive');
  const base=projectInternetIdentity(raw,{slotDomain:slots});
  const keyInt=resourceKeyInteger(base.resourceKey);
  const supercellId=BigInt(base.slotId);
  const microcellId=(keyInt/slots)%microcells;
  const routingDomain=slots*microcells;
  const routingCoordinate=supercellId*microcells+microcellId;
  return Object.freeze({
    ...base,
    schema:'deus-internet-resource-projection/2',
    supercellId:supercellId.toString(),
    microcellId:microcellId.toString(),
    microcellDomain:microcells.toString(),
    routingCoordinate:routingCoordinate.toString(),
    routingDomain:routingDomain.toString(),
    bucketKey:supercellId.toString()+':'+microcellId.toString(),
    collisionKey:base.resourceKey,
    locator:'deus://internet/v2/'+supercellId.toString()+'/'+microcellId.toString()+'/'+base.resourceKey,
    truthBoundary:'SUPERCELL_AND_MICROCELL_ARE_ROUTING_COORDINATES__FULL_RESOURCE_KEY_DISAMBIGUATES_COLLISIONS__PROJECTED_NE_OBSERVED_NE_LIVE_NE_EXECUTABLE',
  });
}

export function cidrCardinality(cidr){
  const parsed=parseCidr(cidr);
  return Object.freeze({
    family:parsed.family,
    cidr:parsed.canonical,
    addressCount:(1n<<BigInt(parsed.hostBits)).toString(),
  });
}

export function projectCidrAddress(cidr,offset,{slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN}={}){
  const parsed=parseCidr(cidr);
  const index=BigInt(offset);
  const count=1n<<BigInt(parsed.hostBits);
  if(index<0n||index>=count) throw new Error('CIDR member offset out of range');
  const numeric=parsed.network+index;
  const address=parsed.family==='ipv6'?formatIpv6(numeric):formatIpv4(numeric);
  const projection=projectInternetIdentity({type:parsed.family,value:address},{slotDomain});
  return Object.freeze({
    schema:'deus-internet-cidr-member-projection/1',
    cidr:parsed.canonical,
    offset:index.toString(),
    addressCount:count.toString(),
    ...projection,
    truthBoundary:'VIRTUAL_PER_ADDRESS_MAPPING_NE_NETWORK_PROBE_NE_LIVENESS_NE_SERVICE_NE_COMPUTE',
  });
}


export function compileCidrAddressDescriptor(cidr,{
  slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN,
  microcellDomain=INTERNET_MICROCELL_DOMAIN,
}={}){
  const parsed=parseCidr(cidr);
  const slots=BigInt(slotDomain);
  const microcells=BigInt(microcellDomain);
  if(slots<=0n||microcells<=0n) throw new Error('routing domains must be positive');
  const addressCount=1n<<BigInt(parsed.hostBits);
  const core={
    schema:'deus-internet-cidr-generative-descriptor/2',
    cidr:parsed.canonical,
    family:parsed.family,
    prefix:parsed.prefix,
    hostBits:parsed.hostBits,
    networkInteger:parsed.network.toString(),
    addressCount:addressCount.toString(),
    slotDomain:slots.toString(),
    microcellDomain:microcells.toString(),
    routingDomain:(slots*microcells).toString(),
    materializedMembers:0,
    storageModel:'DESCRIPTOR_ONLY_GENERATIVE',
    generator:'ADDRESS=NETWORK_PLUS_OFFSET__RESOURCE_KEY=SHA256(TYPE_PIPE_CANONICAL_ADDRESS)',
    activationModel:'SPARSE_HOT_OVERLAY_ONLY',
    truthBoundary:'DESCRIPTOR_DECLARES_ADDRESSABILITY_NE_ENUMERATED_MEMBERS_NE_OBSERVATION_NE_LIVENESS_NE_EXECUTION_AUTHORITY',
  };
  return Object.freeze({...core,descriptorDigest:sha256Json(core)});
}

export function resolveCidrAddressHandle(cidr,offset,{
  slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN,
  microcellDomain=INTERNET_MICROCELL_DOMAIN,
}={}){
  const descriptor=compileCidrAddressDescriptor(cidr,{slotDomain,microcellDomain});
  const parsed=parseCidr(descriptor.cidr);
  const index=BigInt(offset);
  const count=BigInt(descriptor.addressCount);
  if(index<0n||index>=count) throw new Error('CIDR member offset out of range');
  const numeric=parsed.network+index;
  const address=parsed.family==='ipv6'?formatIpv6(numeric):formatIpv4(numeric);
  const projection=projectInternetIdentityHierarchical({type:parsed.family,value:address},{slotDomain,microcellDomain});
  return Object.freeze({
    schema:'deus-internet-address-handle/2',
    descriptorDigest:descriptor.descriptorDigest,
    cidr:descriptor.cidr,
    offset:index.toString(),
    addressCount:descriptor.addressCount,
    ...projection,
    activationState:'VIRTUAL_COLD',
    persistence:'NONE_UNTIL_ACTIVATED',
    truthBoundary:'ADDRESS_HANDLE_IS_GENERATED_ON_DEMAND__NO_MEMBER_ROW_REQUIRED__HANDLE_NE_OBSERVED_HOST_NE_LIVE_SERVICE_NE_EXECUTION_AUTHORITY',
  });
}

export function activateCidrAddress(cidr,offset,{
  slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN,
  microcellDomain=INTERNET_MICROCELL_DOMAIN,
  activatedAt=new Date().toISOString(),
  ttlMs=null,
  metadata={},
}={}){
  const handle=resolveCidrAddressHandle(cidr,offset,{slotDomain,microcellDomain});
  let expiresAt=null;
  if(ttlMs!=null){
    const ttl=Number(ttlMs);
    if(!Number.isFinite(ttl)||ttl<0) throw new Error('ttlMs must be a non-negative finite number');
    const start=Date.parse(String(activatedAt));
    if(!Number.isFinite(start)) throw new Error('activatedAt must be an ISO timestamp when ttlMs is used');
    expiresAt=new Date(start+ttl).toISOString();
  }
  const core={
    ...handle,
    schema:'deus-internet-address-activation/2',
    activationState:'HOT_SPARSE',
    activatedAt:String(activatedAt),
    expiresAt,
    persistence:'SPARSE_OVERLAY_ONLY',
    metadata:clone(metadata),
    truthBoundary:'HOT_ACTIVATION_IS_SPARSE_KERNEL_STATE__VIRTUAL_ADDRESSABILITY_DOES_NOT_REQUIRE_PERSISTING_ALL_MEMBERS',
  };
  return Object.freeze({...core,activationDigest:sha256Json(core)});
}

export function compileGenerativeAddressFabric({
  cidrs=[],
  activated=[],
  slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN,
  microcellDomain=INTERNET_MICROCELL_DOMAIN,
  maxActivated=4096,
}={}){
  if(!Array.isArray(cidrs)) throw new Error('cidrs must be an array');
  if(!Array.isArray(activated)) throw new Error('activated must be an array');
  const hotLimit=Math.trunc(Number(maxActivated));
  if(!Number.isFinite(hotLimit)||hotLimit<0) throw new Error('maxActivated must be a non-negative integer');
  if(activated.length>hotLimit) throw new Error('activated sparse overlay exceeds maxActivated');
  const descriptors=cidrs.map(cidr=>compileCidrAddressDescriptor(cidr,{slotDomain,microcellDomain}));
  const virtualAddressCount=descriptors.reduce((sum,x)=>sum+BigInt(x.addressCount),0n);
  const hot=activated.map((entry,index)=>{
    if(entry&&typeof entry==='object'&&entry.cidr!=null){
      return activateCidrAddress(entry.cidr,entry.offset??0n,{
        slotDomain,microcellDomain,
        activatedAt:entry.activatedAt??new Date(0).toISOString(),
        ttlMs:entry.ttlMs??null,
        metadata:entry.metadata??{index},
      });
    }
    const projection=projectInternetIdentityHierarchical(entry,{slotDomain,microcellDomain});
    return Object.freeze({
      ...projection,
      schema:'deus-internet-address-activation/2',
      activationState:'HOT_SPARSE',
      persistence:'SPARSE_OVERLAY_ONLY',
      metadata:{index},
      truthBoundary:'HOT_ACTIVATION_IS_SPARSE_KERNEL_STATE__PROJECTED_IDENTITY_NE_OBSERVED_HOST_NE_LIVE_SERVICE',
    });
  });
  const buckets=new Map();
  for(const item of hot) buckets.set(item.bucketKey,(buckets.get(item.bucketKey)??0)+1);
  const depths=[...buckets.values()];
  const payload={
    schema:INTERNET_GENERATIVE_ADDRESS_FABRIC_VERSION,
    slotDomain:BigInt(slotDomain).toString(),
    microcellDomain:BigInt(microcellDomain).toString(),
    routingDomain:(BigInt(slotDomain)*BigInt(microcellDomain)).toString(),
    descriptorCount:descriptors.length,
    virtualAddressCount:virtualAddressCount.toString(),
    materializedHotIdentities:hot.length,
    hotBucketCount:buckets.size,
    hotCollisionBuckets:depths.filter(x=>x>1).length,
    maxHotBucketDepth:depths.length?Math.max(...depths):0,
    descriptors,
    hot,
    storageModel:'O(DESCRIPTORS_PLUS_HOT_OVERLAY)_NOT_O(VIRTUAL_ADDRESS_COUNT)',
    collisionModel:'1T_SUPERCELL_PLUS_64BIT_MICROCELL_FOR_ROUTING__FULL_256BIT_RESOURCE_KEY_FOR_FINAL_DISAMBIGUATION',
    truthBoundary:'FULL_GENERATIVE_ADDRESSABILITY_NE_FULL_MATERIALIZATION__COLD_DESCRIPTOR_NE_HOT_STATE__ADDRESSABLE_NE_OBSERVED_NE_LIVE_NE_EXECUTABLE',
  };
  return Object.freeze({...payload,fabricDigest:sha256Json(payload)});
}

function computeCategory(entry={}){
  const text=[
    entry.resourceClass,entry.RESOURCE_CLASS,entry.taskScope,entry.TASK_SCOPE,
    entry.platform,entry.PLATFORM,entry.routeRoot,entry.ROUTE_ROOT,
  ].filter(Boolean).join(' ').toLowerCase();
  if(/gpu|cuda|accelerator|tpu/.test(text)) return 'GPU_ACCELERATOR';
  if(/llm|model inference|public_model_inference|inference/.test(text)) return 'MODEL_LLM_INFERENCE';
  if(/cpu|serverless|edge_runtime|hosted_cpu|app_runtime|remote_cpu|sandbox/.test(text)) return 'CPU_RUNTIME';
  if(/compile|compiler|language_compile/.test(text)) return 'COMPILER_EXEC';
  if(/render|chart|diagram|screenshot|image|uml|qr codec|code_to_image/.test(text)) return 'RENDER_MEDIA_CODEC';
  if(/validate|static_analysis|vulnerab|osv/.test(text)) return 'VALIDATION_SECURITY_ANALYSIS';
  if(/drive|workspace|dataflow|document|transform|storage/.test(text)) return 'WORKSPACE_STORAGE_TRANSFORM';
  if(/metadata|retrieval|search|registry|rdap|crossref|openalex|geocode|weather|lexical/.test(text)) return 'DATA_KNOWLEDGE_API';
  return 'OTHER_FUNCTIONAL';
}
function historicalPositive(entry={}){
  const value=String(entry.effectiveCredit??entry.EFFECTIVE_CREDIT??'').toUpperCase();
  return value==='1'||value.startsWith('POSITIVE');
}
function executionVerified(entry={}){
  const value=String(entry.executableState??entry.EXECUTABLE_STATE??'').toUpperCase();
  return value.includes('EXECUTED_VERIFIED')||value.includes('RECEIPT_OBSERVED');
}

export function classifyComputeRegistry(entries=[],{now=Date.now(),maxFreshAgeMs=3600000}={}){
  if(!Array.isArray(entries)) throw new Error('compute registry entries must be an array');
  const ageLimit=num(maxFreshAgeMs,'maxFreshAgeMs',3600000);
  const routes=entries.map((entry,index)=>{
    const id=String(entry.mapId??entry.MAP_ID??entry.id??('route-'+(index+1)));
    const credit=historicalPositive(entry);
    const verified=executionVerified(entry);
    const stamp=entry.currentEvidenceAt??entry.lastVerifiedUtc??entry.LAST_VERIFIED_UTC??entry.observedAt??null;
    const parsed=stamp==null?NaN:Date.parse(String(stamp));
    const fresh=Number.isFinite(parsed)&&Math.max(0,now-parsed)<=ageLimit;
    const receipt=entry.currentExecutionReceipt??entry.executionReceipt??null;
    const admission=credit&&verified&&fresh&&receipt
      ?'CURRENT_ADMITTED'
      :(credit&&verified?'FRESHNESS_CANARY_REQUIRED':'NO_EXECUTION_CREDIT');
    return Object.freeze({
      id,
      category:computeCategory(entry),
      historicalPositive:credit,
      executionVerified:verified,
      evidenceAt:Number.isFinite(parsed)?new Date(parsed).toISOString():null,
      freshness:fresh?'FRESH':'STALE_OR_UNKNOWN',
      admission,
      currentExecutionReceipt:receipt==null?null:String(receipt),
      routeRoot:String(entry.routeRoot??entry.ROUTE_ROOT??id),
      platform:String(entry.platform??entry.PLATFORM??'UNKNOWN'),
    });
  });
  const categories={};
  for(const route of routes) categories[route.category]=(categories[route.category]??0)+1;
  const payload={
    schema:'deus-internet-compute-registry-classification/1',
    total:routes.length,
    historicalPositive:routes.filter(x=>x.historicalPositive).length,
    currentAdmitted:routes.filter(x=>x.admission==='CURRENT_ADMITTED').length,
    freshnessRequired:routes.filter(x=>x.admission==='FRESHNESS_CANARY_REQUIRED').length,
    categories,
    routes,
    truthBoundary:'HISTORICALLY_VERIFIED_NE_CURRENT_ADMITTED__CURRENT_COMPUTE_REQUIRES_FRESH_EVIDENCE_AND_ATTRIBUTABLE_EXECUTION_RECEIPT',
  };
  return Object.freeze({...payload,digest:sha256Json(payload)});
}

export function compileInternetObservatoryKernel({
  identities=[],cidrs=[],computeRoutes=[],now=Date.now(),slotDomain=INTERNET_ADDRESS_SLOT_DOMAIN,maxFreshAgeMs=3600000,
}={}){
  const projected=identities.map(x=>projectInternetIdentity(x,{slotDomain}));
  const cidrCoverage=cidrs.map(cidr=>{
    const card=cidrCardinality(cidr);
    const count=BigInt(card.addressCount);
    return Object.freeze({
      ...card,
      first:projectCidrAddress(cidr,0n,{slotDomain}),
      last:projectCidrAddress(cidr,count-1n,{slotDomain}),
    });
  });
  const addressFabric=compileGenerativeAddressFabric({cidrs,slotDomain});
  const compute=classifyComputeRegistry(computeRoutes,{now,maxFreshAgeMs});
  const virtualAddressCount=addressFabric.virtualAddressCount;
  const payload={
    schema:INTERNET_OBSERVATORY_KERNEL_VERSION,
    slotDomain:BigInt(slotDomain).toString(),
    materializedIdentityCount:projected.length,
    virtualCidrFamilies:cidrCoverage.length,
    virtualAddressCount,
    projected,
    cidrCoverage,
    addressFabric,
    compute,
    truthBoundary:'FULL_VIRTUAL_ADDRESSABILITY_NE_FULL_OBSERVATION__GENERATIVE_ADDRESSABILITY_NE_MATERIALIZED_STATE__OBSERVED_NE_LIVE__LIVE_NE_USABLE__ROUTE_SELECTED_NE_EXECUTED',
  };
  return Object.freeze({...payload,kernelDigest:sha256Json(payload)});
}
