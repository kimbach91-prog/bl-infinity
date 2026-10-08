/**
 * Task-fit hint resolver for an EXISTING, host-admitted InstructionFabric.
 * Atlas/skill metadata are discovery hints only: never credentials, grants or liveness.
 * This module does not create bindings, workers, leases or a new capability registry.
 */
const VALID=/^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,159}$/;
const HASH=/^[a-f0-9]{64}$/;
function fail(code){const e=new Error(code);e.code=code;throw e;}
function ident(x){if(typeof x!=='string'||!VALID.test(x))fail('BAD_ROUTE_DESCRIPTOR');return x;}

/**
 * hostSkills MUST be installed by the authorized host, not hydrated from
 * untrusted Atlas rows. Even a forged hostSkills row cannot create executor
 * authority: fabric.authorize and code pinning remain authoritative.
 */
export function resolveTaskCapability({fabric,hostSkills,intent,dataClass='public',tenantId='deus',sideEffect=false}={}) {
  if(!fabric?.bindings||!fabric?.operators||typeof fabric.authorize!=='function')fail('ADMITTED_FABRIC_REQUIRED');
  if(!Array.isArray(hostSkills)||hostSkills.length>256)fail('BOUNDED_HOST_SKILLS_REQUIRED');
  ident(intent);ident(dataClass);ident(tenantId);
  if(sideEffect===true)fail('SIDE_EFFECT_ROUTE_HOLD');
  const observations=[],accepted=[],seen=new Set();
  for(const entry of hostSkills) {
    if(!entry||typeof entry!=='object')fail('BAD_ROUTE_DESCRIPTOR');
    const skillId=ident(entry.skillId),routeId=ident(entry.routeId),operatorId=ident(entry.operatorId);
    if(seen.has(skillId))fail('AMBIGUOUS_SKILL_ID');
    seen.add(skillId);
    const reason=(code)=>observations.push({skillId,routeId,operatorId,verdict:'HOLD',code});
    if(entry.intent!==intent){reason('INTENT_MISMATCH');continue;}
    if(entry.dataClass!==dataClass){reason('DATA_CLASS_MISMATCH');continue;}
    if(entry.costUsd!==0){reason('NONZERO_OR_UNKNOWN_COST');continue;}
    if(!HASH.test(entry.programDigest||'')){reason('MISSING_PROGRAM_PIN');continue;}
    const op=fabric.operators.get(operatorId);
    if(!op||op.programDigest!==entry.programDigest){reason('OPERATOR_PIN_MISMATCH');continue;}
    try{
      const {b}=fabric.authorize(routeId,operatorId,{dataClass,tenantId,sideEffect:false});
      if(!b.operatorIds.includes(operatorId)){reason('OPERATOR_NOT_IN_BINDING');continue;}
      accepted.push({skillId,routeId,operatorId,intent,dataClass,programDigest:entry.programDigest,bindingDigest:b.bindingHash,priority:Number.isSafeInteger(entry.priority)&&entry.priority>=0?entry.priority:1000});
      observations.push({skillId,routeId,operatorId,verdict:'ELIGIBLE_FOR_PROBE',code:'EXISTING_HOST_BINDING'});
    }catch(e){reason(e?.code||'NOT_AUTHORIZED');}
  }
  accepted.sort((a,b)=>a.priority-b.priority||a.skillId.localeCompare(b.skillId));
  if(!accepted.length)return {state:'HOLD_NO_ADMITTED_ROUTE',selected:null,observations};
  return {state:'CANDIDATE_NEEDS_FRESH_CANARY_AND_RECEIPT',selected:accepted[0],observations};
}
