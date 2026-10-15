// PUBLIC fixture-only recall reference; NOT an admitted native dispatcher.
import {createHash} from 'node:crypto';
const digest=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const fail=x=>{throw Object.assign(new Error(x),{code:x});};
const required=['id','version','principal','domain','input','output','effect','resource','sourcePin','verifier','rollback'];
export function validate(c){
  for(const k of required)if(typeof c?.[k]!=='string'||!c[k])fail('MISSING_'+k);
  if(!/^\d+\.\d+\.\d+$/.test(c.version))fail('BAD_VERSION');
  if(!/^[a-f0-9]{64}$/.test(c.sourcePin))fail('BAD_PIN');
  if(!Array.isArray(c.aliases)||c.aliases.some(x=>typeof x!=='string'||!x))fail('BAD_ALIASES');
  return c;
}
export function recall(catalog,q){
  if(!q||typeof q.name!=='string'||!q.name)fail('NAME_REQUIRED');
  for(const k of ['version','principal','domain','sourcePin'])if(typeof q[k]!=='string'||!q[k])fail('QUERY_'+k);
  const named=catalog.filter(c=>c?.id===q.name||(Array.isArray(c?.aliases)&&c.aliases.includes(q.name)));
  const selected=named.filter(c=>c.version===q.version&&c.principal===q.principal&&c.domain===q.domain);
  if(!selected.length)fail(named.length?'EXACT_VERSION_PRINCIPAL_DOMAIN_MISSING':'UNKNOWN_CAPABILITY');
  if(selected.length>1)fail('AMBIGUOUS_EXACT_MATCH');
  const c=validate(selected[0]);
  if(c.sourcePin!==q.sourcePin)fail('PIN_MISMATCH');
  return {id:c.id,version:c.version,principal:c.principal,domain:c.domain,sourcePin:c.sourcePin,
    history:c.history||'UNKNOWN',route:c.route||'UNKNOWN',admission:'NOT_ESTABLISHED_BY_RECALL',
    receipt:null,identityHash:digest([c.id,c.version,c.principal,c.domain,c.sourcePin])};
}
export function admissionGate(rec,verified){
  if(rec?.admission!=='NOT_ESTABLISHED_BY_RECALL')fail('RECALL_REQUIRED');
  const pass=verified?.authenticated===true&&verified?.current===true&&verified?.taskBound===true
    &&verified?.leaseValid===true&&verified?.revoked===false
    &&verified?.principal===rec.principal&&verified?.domain===rec.domain
    &&verified?.handlerPin===rec.sourcePin;
  return {state:pass?'HOST_DISPATCH_ELIGIBLE_ONLY':'HOLD_ADMISSION',
    executed:false,acknowledged:false,receipt:null};
}
