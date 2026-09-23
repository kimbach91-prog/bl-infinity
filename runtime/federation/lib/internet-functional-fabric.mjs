import { sha256Json } from './canonical.mjs';
import { compileLogicalMicrocellShards, ONE_T_LOGICAL_NAMESPACE } from './logical-resource-compiler.mjs';

export const INTERNET_FUNCTIONAL_FABRIC_VERSION='deus-internet-functional-fabric/2.0';
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
function routeMetrics(resource,capability,required,freshness,requireReceipt){
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
  return Object.freeze({
    posteriorUseful,
    expectedVerifiedUsefulResult,
    marginalValue:expectedVerifiedUsefulResult/denominator,
    freshness,
    latencyMs:latency,
    costPerUnitUsd:resource.telemetry.costPerUnitUsd,
    cacheHitProbability:cacheHit,
    receiptCapable:receiptCompatible(resource,capability,required),
  });
}

export function evaluateTaskFitRoutes(atlas,{
  capability,operatorAbi=null,dataClass='BL-S0',namespace='deus://internet/',namespaceIndex=null,
  maxRoutes=8,now=Date.now(),requireIndependent=false,requireReceipt=false,
  maxEvidenceAgeMs=null,minTrust=0,maxCostPerUnitUsd=null,requireKnownQuota=false,
}={}){
  const required=normalizeCapabilitySignature(operatorAbi??capability);
  const evidenceAge=maxEvidenceAgeMs==null?null:num(maxEvidenceAgeMs,'maxEvidenceAgeMs');
  const minimumTrust=Math.min(1,num(minTrust,'minTrust',0));
  const costCeiling=maxCostPerUnitUsd==null?null:num(maxCostPerUnitUsd,'maxCostPerUnitUsd');
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
    const metrics=routeMetrics(resource,matched,required,freshness,requireReceipt);
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
    truthBoundary:'ROUTE_SELECTED_NE_ROUTE_EXECUTED__POSTERIOR_AND_MARGINAL_VALUE_ARE_TASK_SELECTION_METRICS__PHYSICAL_CREDIT_REQUIRES_RECEIPT',
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
