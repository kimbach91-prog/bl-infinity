/** Cost selection ABOVE, never instead of, existing InstructionFabric gates.
 * Host-installed candidates only. No endpoints, credentials, shell or new leases.
 * Profiles are scoped recommendations, not attestations or portable throughput.
 */
import { executeAtomGraph } from './instruction-fabric.mjs';
import { sha256Json } from './canonical.mjs';
export const EXECUTION_PORTFOLIO_VERSION='deus-execution-portfolio/0.1';
const need=(ok,code)=>{if(!ok){const e=new Error(code);e.code=code;throw e;}};
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
export function chooseExecution({contract,candidates,profiles=[],budget,now=Date.now()}){
  need(contract&&hash(contract.semanticDigest)&&hash(contract.environmentDigest),'CONTRACT_DIGESTS');
  need(contract.sideEffects===false,'PURE_TASKS_ONLY');
  need(budget&&Number.isSafeInteger(budget.cpuThreads)&&budget.cpuThreads>0&&Number.isFinite(budget.ramBytes)&&budget.ramBytes>0,'HOST_BUDGET_REQUIRED');
  need(Array.isArray(candidates)&&candidates.length>0&&candidates.length<=32,'BOUNDED_CANDIDATES');
  need(new Set(candidates.map(c=>c.id)).size===candidates.length,'DUPLICATE_CANDIDATE');
  const eligible=[],rejected=[];
  for(const c of candidates){
    let why=null;
    if(!['DIRECT_ATOM','ATOM_GRAPH'].includes(c.kind))why='UNKNOWN_KIND';
    else if(c.semanticDigest!==contract.semanticDigest)why='SEMANTIC_MISMATCH';
    else if(!Number.isFinite(c.ramBytes)||c.ramBytes<0||c.ramBytes>budget.ramBytes)why='RAM_BUDGET';
    else if(!Number.isSafeInteger(c.cpuThreads)||c.cpuThreads<1||c.cpuThreads>budget.cpuThreads)why='CPU_BUDGET';
    else if(c.gpuRequired&&!budget.gpuAvailable)why='GPU_NOT_ADMITTED';
    else if(contract.requireGraphCheckpoints&&c.kind!=='ATOM_GRAPH')why='CHECKPOINT_CONTRACT';
    let p;
    if(!why){p=profiles.filter(p=>p.candidateId===c.id&&p.semanticDigest===contract.semanticDigest&&p.environmentDigest===contract.environmentDigest&&p.workloadBucket===contract.workloadBucket&&p.mode===contract.mode&&p.verified===true&&p.samples>=3&&p.expiresAt>now&&Number.isFinite(p.e2eMs)&&p.e2eMs>=0).sort((a,b)=>b.observedAt-a.observedAt)[0];
      if(!p&&!c.defaultSafe)why='UNMEASURED_VARIANT';}
    if(why)rejected.push({id:c.id,reason:why});
    else eligible.push({candidate:c,cost:p?.e2eMs??Infinity,profile:p??null});
  }
  need(eligible.length,'NO_ELIGIBLE_EXECUTION_PLAN');
  eligible.sort((a,b)=>a.cost-b.cost||Number(b.candidate.defaultSafe)-Number(a.candidate.defaultSafe)||a.candidate.id.localeCompare(b.candidate.id));
  const e=eligible[0];
  return {schema:EXECUTION_PORTFOLIO_VERSION,state:'PROPOSED',selected:e.candidate.id,kind:e.candidate.kind,
    estimatedE2eMs:Number.isFinite(e.cost)?e.cost:null,profileReceipt:e.profile?.receiptId??null,
    coldSafeFallback:e.profile===null,rejected,contractDigest:sha256Json(contract),
    executionAuthorized:false,requires:'EXISTING_AUTHORIZE_PROBE_LEASE_PIN_VERIFY_RELEASE'};
}
export async function executeSelected({fabric,runtime,contract,candidates,profiles,budget,context={}}){
  need(context.sideEffect!==true,'PURE_CONTEXT_REQUIRED');
  const plan=chooseExecution({contract,candidates,profiles,budget});
  const c=candidates.find(c=>c.id===plan.selected);const started=performance.now();let value,detail;
  // No raw operator call is exposed by this selector. Both paths use the old gates.
  if(c.kind==='DIRECT_ATOM'){
    const r=await fabric.invoke(c.routeId,c.operatorId,c.input,context);
    value=r.value;detail={executions:r.receipt.kind==='VERIFIED_REUSE'?0:1,reuses:r.receipt.kind==='VERIFIED_REUSE'?1:0,receipt:r.receipt};
  }else{
    need((context.tenantId??'deus')==='deus','GRAPH_TENANT_CONTEXT_UNSUPPORTED');
    need(c.graph.dataClass===(context.dataClass??'public'),'GRAPH_DATA_CLASS');
    // executeAtomGraph uses the existing queue; do not attach unrelated jobs.
    const r=await executeAtomGraph({fabric,runtime,graph:c.graph,maxParallel:Math.min(c.cpuThreads,budget.cpuThreads),deadlineMs:c.deadlineMs??120000});
    value=r.root;detail={executions:r.executions,reuses:r.reuses,resourceState:r.resourceState};
  }
  const receipt={schema:EXECUTION_PORTFOLIO_VERSION,state:'EXECUTED_THROUGH_EXISTING_FABRIC',plan,detail,
    elapsedMs:performance.now()-started,outputDigest:sha256Json(value),
    verifiedBy:'EXISTING_OPERATOR_VERIFIER',globalAdoption:false,physicalCapacityClaimed:false};
  fabric.store.event('PORTFOLIO_RESULT',{planDigest:sha256Json(plan),outputDigest:receipt.outputDigest,kind:c.kind});
  return {value,receipt};
}
