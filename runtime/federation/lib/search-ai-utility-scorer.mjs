import { sha256Json } from './canonical.mjs';

export const SEARCH_AI_UTILITY_SCORER_VERSION='deus-search-ai-utility-scorer/1.0';
export const SEARCH_AI_SELECTION_SCHEMA='deus-search-ai-route-selection/1.0';

const EXECUTION_STATES=['ROUTABLE','EXECUTED_VERIFIED','VERIFIED_ROUTABLE','LOCAL_ROUTABLE'];
const BLOCKED_STATES=['RETIRED','REVOKED','BLOCKED_SECURITY','DISABLED'];

function str(v,name){
  const x=String(v??'').trim();
  if(!x) throw new Error(name+' required');
  return x;
}
function nonNegative(v,name,fallback=0){
  const n=Number(v??fallback);
  if(!Number.isFinite(n)||n<0) throw new Error(name+' must be non-negative');
  return n;
}
function bounded01(v,name,fallback=null){
  if(v==null||v==='') return fallback;
  const n=Number(v);
  if(!Number.isFinite(n)||n<0||n>1) throw new Error(name+' must be in [0,1]');
  return n;
}
function count(v,name){return Math.trunc(nonNegative(v,name,0));}
function bool(v,fallback=false){
  if(v==null) return fallback;
  if(typeof v==='boolean') return v;
  const s=String(v).trim().toLowerCase();
  if(s==='true'||s==='1'||s==='yes') return true;
  if(s==='false'||s==='0'||s==='no') return false;
  return fallback;
}
function stateTokens(v){
  return String(v??'').toUpperCase().split(/[|/]/).map(x=>x.trim()).filter(Boolean);
}
function executionStateAllowed(v){
  const tokens=stateTokens(v);
  return EXECUTION_STATES.some(allow=>tokens.some(t=>t===allow||t.startsWith(allow+'_')||t.includes(allow)));
}
function blockedState(v){
  const tokens=stateTokens(v);
  return BLOCKED_STATES.some(block=>tokens.some(t=>t===block||t.startsWith(block+'_')));
}
function taskMatch(profileTask,requested){
  if(requested==null||requested===''||requested==='ANY') return true;
  const p=String(profileTask).toUpperCase();
  const r=String(requested).toUpperCase();
  return p==='ANY'||p===r||p.startsWith(r+'.')||r.startsWith(p+'.');
}
function runningMean(previousMean,previousCount,value){
  if(value==null) return {mean:previousMean,count:previousCount};
  const nextCount=previousCount+1;
  const base=previousCount===0||previousMean==null?0:Number(previousMean)*previousCount;
  return {mean:(base+Number(value))/nextCount,count:nextCount};
}

export function normalizeSearchAiProfile(raw={}){
  const rootId=str(raw.rootId??raw.ROOT_ID??raw.id,'profile.rootId');
  const namespace=str(raw.namespace??raw.NAMESPACE,'profile.namespace');
  if(!namespace.startsWith('deus://search-ai/')) throw new Error('profile.namespace must use deus://search-ai/');
  const receiptCount=count(raw.receiptCount??raw.RECEIPT_COUNT??raw.resultCount??raw.RESULT_COUNT,'profile.receiptCount');
  const successCount=count(raw.successCount??raw.SUCCESS_COUNT,'profile.successCount');
  const failureScars=count(raw.failureScars??raw.FAILURE_SCARS,'profile.failureScars');
  if(successCount>receiptCount) throw new Error('profile.successCount cannot exceed receiptCount');
  return Object.freeze({
    schema:SEARCH_AI_UTILITY_SCORER_VERSION,
    rootId,
    provider:str(raw.provider??raw.PROVIDER,'profile.provider'),
    surface:str(raw.surface??raw.SURFACE,'profile.surface'),
    namespace,
    taskFamily:String(raw.taskFamily??raw.TASK_FAMILY??'SEARCH_RESEARCH').trim().toUpperCase(),
    routeState:String(raw.routeState??raw.ROUTE_STATE??'DISCOVERED').trim().toUpperCase(),
    authScope:String(raw.authScope??raw.AUTH_SCOPE??'UNBOUND').trim(),
    executionAuthorized:bool(raw.executionAuthorized??raw.EXECUTION_AUTHORIZED,false),
    qualityMean:bounded01(raw.qualityMean??raw.QUALITY_MEAN,'profile.qualityMean',null),
    qualityCount:count(raw.qualityCount??raw.QUALITY_COUNT,'profile.qualityCount'),
    latencyMeanMs:raw.latencyMeanMs==null&&raw.LATENCY_MEAN_MS==null?null:nonNegative(raw.latencyMeanMs??raw.LATENCY_MEAN_MS,'profile.latencyMeanMs'),
    latencyCount:count(raw.latencyCount??raw.LATENCY_COUNT,'profile.latencyCount'),
    costMeanUsd:raw.costMeanUsd==null&&raw.COST_MEAN_USD==null?null:nonNegative(raw.costMeanUsd??raw.COST_MEAN_USD,'profile.costMeanUsd'),
    costCount:count(raw.costCount??raw.COST_COUNT,'profile.costCount'),
    freshnessFactor:bounded01(raw.freshnessFactor??raw.FRESHNESS_FACTOR,'profile.freshnessFactor',null),
    reuseCount:count(raw.reuseCount??raw.REUSE_COUNT,'profile.reuseCount'),
    receiptCount,
    successCount,
    failureScars,
    lastResultRef:raw.lastResultRef??raw.LAST_RESULT_REF?String(raw.lastResultRef??raw.LAST_RESULT_REF):null,
    sourceRef:raw.sourceRef??raw.SOURCE_REF?String(raw.sourceRef??raw.SOURCE_REF):null,
    metadata:structuredClone(raw.metadata??{}),
  });
}

export function scoreSearchAiProfile(profile,{mode='DISCOVERY'}={}){
  const p=normalizeSearchAiProfile(profile);
  const execution=String(mode).toUpperCase()==='EXECUTION';
  const quality=p.qualityMean??0.5;
  const freshness=p.freshnessFactor??(execution?0.5:0.7);
  const successPosterior=(p.successCount+1)/(p.receiptCount+2);
  const evidenceFactor=0.8+0.2*Math.min(1,p.receiptCount/3);
  const reuseBonus=1+Math.min(0.20,Math.log1p(p.reuseCount)*0.04);
  const latencyMs=p.latencyMeanMs??1500;
  const latencyPenalty=1+latencyMs/2000;
  const costUsd=p.costMeanUsd??0;
  const costPenalty=1+costUsd*1000;
  const scarPenalty=1+p.failureScars/(p.successCount+1);
  const utility=(quality*successPosterior*freshness*evidenceFactor*reuseBonus)/
    (latencyPenalty*costPenalty*scarPenalty);
  return Object.freeze({
    rootId:p.rootId,
    utilityScore:utility,
    quality,
    freshnessFactor:freshness,
    successPosterior,
    evidenceFactor,
    reuseBonus,
    latencyPenalty,
    costPenalty,
    scarPenalty,
    truthBoundary:'UTILITY_SCORE_IS_TASK_ROUTING_EVIDENCE_NOT_BACKEND_CAPACITY_OR_PROVIDER_OWNERSHIP',
  });
}

export function applySearchAiResultReceipt(profile,receipt={}){
  const p=normalizeSearchAiProfile(profile);
  const success=receipt.success===true;
  const resultRef=str(receipt.resultRef,'receipt.resultRef');
  const qualityValue=bounded01(receipt.qualityScore,'receipt.qualityScore',null);
  const freshnessValue=bounded01(receipt.freshnessFactor,'receipt.freshnessFactor',p.freshnessFactor);
  const latencyValue=receipt.latencyMs==null?null:nonNegative(receipt.latencyMs,'receipt.latencyMs');
  const costValue=receipt.costUsd==null?null:nonNegative(receipt.costUsd,'receipt.costUsd');
  const q=runningMean(p.qualityMean,p.qualityCount,qualityValue);
  const l=runningMean(p.latencyMeanMs,p.latencyCount,latencyValue);
  const c=runningMean(p.costMeanUsd,p.costCount,costValue);
  return normalizeSearchAiProfile({
    ...p,
    qualityMean:q.mean,
    qualityCount:q.count,
    latencyMeanMs:l.mean,
    latencyCount:l.count,
    costMeanUsd:c.mean,
    costCount:c.count,
    freshnessFactor:freshnessValue,
    reuseCount:p.reuseCount+(receipt.reuseHit===true?1:0),
    receiptCount:p.receiptCount+1,
    successCount:p.successCount+(success?1:0),
    failureScars:p.failureScars+(success?0:1),
    lastResultRef:resultRef,
  });
}

export function selectSearchAiRoutes(profiles=[],{
  mode='DISCOVERY',taskFamily='SEARCH_RESEARCH',maxRoutes=3,maxCostUsd=null,
  allowedProviders=null,requireFreshnessAtLeast=0,
}={}){
  if(!Array.isArray(profiles)) throw new Error('profiles must be an array');
  const normalizedMode=String(mode).toUpperCase();
  if(!['DISCOVERY','EXECUTION'].includes(normalizedMode)) throw new Error('mode must be DISCOVERY or EXECUTION');
  const limit=Math.max(1,Math.trunc(nonNegative(maxRoutes,'maxRoutes',3)));
  const costCeiling=maxCostUsd==null?null:nonNegative(maxCostUsd,'maxCostUsd');
  const freshnessFloor=bounded01(requireFreshnessAtLeast,'requireFreshnessAtLeast',0);
  const providerSet=allowedProviders==null?null:new Set(allowedProviders.map(x=>String(x).toLowerCase()));
  const rejectionCounts={};
  const reject=r=>{rejectionCounts[r]=(rejectionCounts[r]??0)+1;};
  const candidates=[];

  for(const raw of profiles){
    const p=normalizeSearchAiProfile(raw);
    if(blockedState(p.routeState)){reject('STATE_BLOCKED');continue;}
    if(!taskMatch(p.taskFamily,taskFamily)){reject('TASK_FAMILY');continue;}
    if(providerSet&&!providerSet.has(p.provider.toLowerCase())){reject('PROVIDER');continue;}
    if((p.freshnessFactor??0)<freshnessFloor){reject('FRESHNESS');continue;}
    if(costCeiling!=null&&(p.costMeanUsd??0)>costCeiling){reject('COST');continue;}

    if(normalizedMode==='EXECUTION'){
      if(p.executionAuthorized!==true){reject('AUTHORITY');continue;}
      if(!executionStateAllowed(p.routeState)){reject('ROUTE_STATE');continue;}
      if(p.receiptCount<1||!p.lastResultRef){reject('EXECUTION_RECEIPT');continue;}
    }
    const score=scoreSearchAiProfile(p,{mode:normalizedMode});
    candidates.push({profile:p,score});
  }

  candidates.sort((a,b)=>b.score.utilityScore-a.score.utilityScore||a.profile.rootId.localeCompare(b.profile.rootId));
  const routes=candidates.slice(0,limit).map(x=>Object.freeze({
    ...x.profile,
    selectionScore:x.score.utilityScore,
    selectionMetrics:x.score,
  }));
  const payload={
    schema:SEARCH_AI_SELECTION_SCHEMA,
    mode:normalizedMode,
    taskFamily:String(taskFamily),
    routes,
    rejectionCounts,
    evaluatedProfiles:profiles.length,
    truthBoundary:'ROUTE_SELECTED_NE_ROUTE_EXECUTED__ADDRESS_MEMORY_NE_AUTHORITY__UTILITY_NE_BACKEND_CAPACITY__PROVIDER_TRAINING_EFFECT_UNKNOWN',
  };
  return Object.freeze({...payload,selectionDigest:sha256Json(payload)});
}
