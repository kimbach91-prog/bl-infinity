import { sha256Json } from './canonical.mjs';
import { compileLogicalMicrocellShards, ONE_T_LOGICAL_NAMESPACE } from './logical-resource-compiler.mjs';

export const INTERNET_FUNCTIONAL_FABRIC_VERSION='deus-internet-functional-fabric/1.0';
export const SUPERCELL_PROFILE='SCALE_FREE_HIERARCHICAL_SYNERGY_V2_PLUS_1T_NAMESPACE';
export const MAX_HOT_ROUTES_DEFAULT=64;

const DATA_RANK=new Map([['PUBLIC',0],['BL-S0',0],['S0',0],['BL-S1',1],['S1',1],['BL-S2',2],['S2',2],['BL-S3',3],['S3',3],['BL-S4',4],['S4',4]]);

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
function clone(v){return v===undefined?undefined:structuredClone(v);}
function uniq(xs){return [...new Set(xs.map(String))];}
function dataRank(v){return DATA_RANK.get(String(v??'PUBLIC').toUpperCase())??99;}

export function internetNamespace(parts=[]){
  const segs=(Array.isArray(parts)?parts:[parts]).flatMap(x=>String(x??'').split('/')).map(x=>x.trim().toLowerCase()).filter(Boolean).map(x=>encodeURIComponent(x));
  if(!segs.length) throw new Error('namespace parts required');
  return 'deus://internet/'+segs.join('/');
}

export function normalizeInternetResource(raw={}){
  const id=str(raw.id,'resource.id');
  const namespace=str(raw.namespace??internetNamespace([raw.family??'resource',id]),'resource.namespace');
  const capabilities=uniq(raw.capabilities??[]);
  if(!capabilities.length) throw new Error('resource '+id+' capabilities required');
  const allowedDataClasses=uniq(raw.authorization?.allowedDataClasses??['PUBLIC']);
  const expiresAt=raw.authorization?.expiresAt==null?null:String(raw.authorization.expiresAt);
  return Object.freeze({
    id,
    namespace,
    family:String(raw.family??'GENERIC').toUpperCase(),
    provider:String(raw.provider??'UNKNOWN'),
    endpoint:raw.endpoint==null?null:String(raw.endpoint),
    protocols:Object.freeze(uniq(raw.protocols??[])),
    capabilities:Object.freeze(capabilities),
    authorization:Object.freeze({
      mode:String(raw.authorization?.mode??'PUBLIC').toUpperCase(),
      standing:raw.authorization?.standing!==false,
      allowedDataClasses:Object.freeze(allowedDataClasses),
      expiresAt,
    }),
    telemetry:Object.freeze({
      trust:Math.min(1,num(raw.telemetry?.trust,'telemetry.trust',0.5)),
      availability:Math.min(1,num(raw.telemetry?.availability,'telemetry.availability',1)),
      p95LatencyMs:raw.telemetry?.p95LatencyMs==null?null:num(raw.telemetry.p95LatencyMs,'telemetry.p95LatencyMs'),
      estimatedBandwidthMbps:raw.telemetry?.estimatedBandwidthMbps==null?null:num(raw.telemetry.estimatedBandwidthMbps,'telemetry.estimatedBandwidthMbps'),
      costPerUnitUsd:num(raw.telemetry?.costPerUnitUsd,'telemetry.costPerUnitUsd',0),
    }),
    rateLimit:clone(raw.rateLimit??null),
    cache:clone(raw.cache??null),
    locality:clone(raw.locality??null),
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
    resources:normalized,
    summary:{
      resources:normalized.length,
      providers:new Set(normalized.map(x=>x.provider)).size,
      families:new Set(normalized.map(x=>x.family)).size,
      capabilityCount:new Set(normalized.flatMap(x=>x.capabilities)).size,
    },
    truthBoundary:'ATLAS_KNOWLEDGE_NE_EXECUTION_AUTHORITY__PUBLIC_NE_UNLIMITED__NAMESPACE_NE_PHYSICAL_WORKER'
  };
  return Object.freeze({...payload,atlasDigest:sha256Json(payload)});
}

function capabilityMatch(resource,required){
  return resource.capabilities.some(c=>c===required || c.startsWith(required+'.') || required.startsWith(c+'.'));
}
function authorizedFor(resource,dataClass,now){
  if(resource.authorization.standing!==true) return false;
  if(resource.authorization.expiresAt && Date.parse(resource.authorization.expiresAt)<=now) return false;
  const need=dataRank(dataClass);
  return resource.authorization.allowedDataClasses.some(x=>dataRank(x)>=need);
}
function routeScore(r){
  const latency=r.telemetry.p95LatencyMs==null?1000:r.telemetry.p95LatencyMs;
  const bandwidth=r.telemetry.estimatedBandwidthMbps??0;
  const cost=r.telemetry.costPerUnitUsd;
  return (r.telemetry.trust*4)+(r.telemetry.availability*3)+Math.log10(1+bandwidth)-Math.log10(1+latency)-(Math.log10(1+cost*1000));
}

export function selectTaskFitRoutes(atlas,{
  capability,
  dataClass='BL-S0',
  maxRoutes=8,
  now=Date.now(),
  requireIndependent=false,
}={}){
  const cap=str(capability,'capability');
  const limit=Math.max(1,Math.trunc(num(maxRoutes,'maxRoutes',8)));
  const candidates=atlas.resources
    .filter(r=>['ACTIVE','VERIFIED','AVAILABLE','EXECUTED_VERIFIED_SCOPED'].includes(r.state))
    .filter(r=>capabilityMatch(r,cap))
    .filter(r=>authorizedFor(r,dataClass,now))
    .map(r=>({resource:r,score:routeScore(r)}))
    .sort((a,b)=>b.score-a.score || a.resource.id.localeCompare(b.resource.id));
  const usedDedup=new Set();
  const usedIndependent=new Set();
  const out=[];
  for(const item of candidates){
    const r=item.resource;
    if(usedDedup.has(r.dedupGroup)) continue;
    if(requireIndependent && usedIndependent.has(r.independenceGroup)) continue;
    out.push(Object.freeze({...r,selectionScore:item.score}));
    usedDedup.add(r.dedupGroup);
    usedIndependent.add(r.independenceGroup);
    if(out.length>=limit) break;
  }
  return Object.freeze(out);
}

export function compileInternetFabricPlan({
  taskId,
  logicalUnits,
  resourceVector,
  resources,
  operators,
  logicalNamespace=ONE_T_LOGICAL_NAMESPACE,
  maxHotRoutes=MAX_HOT_ROUTES_DEFAULT,
  maxPhysicalShards=64,
  dataClass='BL-S0',
  metadata={},
}={}){
  const id=str(taskId,'taskId');
  if(!Array.isArray(operators)||operators.length===0) throw new Error('operators must be non-empty');
  const atlas=compileCapabilityAtlas(resources??[]);
  const shardPlan=compileLogicalMicrocellShards({
    taskId:id,
    logicalUnits,
    logicalNamespace,
    resourceVector,
    maxPhysicalShards,
    metadata:{profile:SUPERCELL_PROFILE}
  });
  const opIds=new Set();
  const compiledOperators=operators.map((op,index)=>{
    const opId=str(op.id??('op-'+(index+1)),'operator.id');
    if(opIds.has(opId)) throw new Error('duplicate operator id '+opId);
    opIds.add(opId);
    const capability=str(op.capability,'operator.capability');
    const deps=uniq(op.deps??[]);
    const routes=selectTaskFitRoutes(atlas,{
      capability,
      dataClass:op.dataClass??dataClass,
      maxRoutes:Math.min(maxHotRoutes,op.maxRoutes??maxHotRoutes),
      requireIndependent:op.requireIndependent===true,
    });
    return Object.freeze({
      id:opId,
      capability,
      deps:Object.freeze(deps),
      logicalWorkUnits:op.logicalWorkUnits==null?null:String(op.logicalWorkUnits),
      state:routes.length?'ROUTABLE':'HOLD_NO_ROUTE',
      routes,
      fallbackPolicy:String(op.fallbackPolicy??'ALTERNATE_ROUTE_THEN_CHECKPOINT'),
      metadata:clone(op.metadata??{}),
    });
  });
  for(const op of compiledOperators) for(const dep of op.deps) if(!opIds.has(dep)) throw new Error('unknown operator dependency '+dep);

  const selectedResourceIds=uniq(compiledOperators.flatMap(o=>o.routes.map(r=>r.id)));
  const hotRouteLimit=Math.min(Math.max(1,Math.trunc(maxHotRoutes)),selectedResourceIds.length||1);
  const payload={
    schema:INTERNET_FUNCTIONAL_FABRIC_VERSION,
    profile:SUPERCELL_PROFILE,
    taskId:id,
    dataClass:String(dataClass),
    logicalNamespace:String(logicalNamespace),
    logicalUnits:String(logicalUnits),
    atlasDigest:atlas.atlasDigest,
    atlasSummary:atlas.summary,
    shardPlan,
    operators:compiledOperators,
    selectedResourceIds:Object.freeze(selectedResourceIds.slice(0,hotRouteLimit)),
    summary:{
      operators:compiledOperators.length,
      routableOperators:compiledOperators.filter(x=>x.state==='ROUTABLE').length,
      heldOperators:compiledOperators.filter(x=>x.state!=='ROUTABLE').length,
      physicalShards:shardPlan.physicalShards,
      addressableLogicalUnits:String(logicalUnits),
      hotRoutes:selectedResourceIds.length,
    },
    metadata:clone(metadata),
    truthBoundary:'ONE_T_IS_LOGICAL_ADDRESS_SPACE__ONLY_BOUNDED_TASK_FIT_ROUTES_MATERIALIZE__ROUTE_FOUND_NE_ROUTE_LIVE__EACH_EXTERNAL_EFFECT_REQUIRES_ITS_OWN_AUTHORITY_AND_RECEIPT__NO_BLIND_SCANNING'
  };
  return Object.freeze({...payload,planDigest:sha256Json(payload)});
}

export function buildCrossCheckSet(atlas,{capability,dataClass='BL-S0',width=3,now=Date.now()}={}){
  return selectTaskFitRoutes(atlas,{capability,dataClass,maxRoutes:width,now,requireIndependent:true});
}
