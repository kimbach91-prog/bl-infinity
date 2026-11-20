// Direct unit tests of the shipped PUBLIC reference module, not a copied recall.
// No host dispatch, private data, credentials, network or production mutation.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {validate, recall, admissionGate} from '../lib/pinned-capability-recall.mjs';

const pin = 'a'.repeat(64);
const record = (patch = {}) => ({
  id:'public.sum', version:'1.0.0', principal:'fixture-a', domain:'fixture-numbers',
  input:'integer[]', output:'integer', effect:'none', resource:'in-process',
  sourcePin:pin, verifier:'exact-integer', rollback:'discard-fixture',
  aliases:['sum'], history:'PASS_SCOPED', route:'UNKNOWN', ...patch
});
const query = (patch = {}) => ({
  name:'sum', version:'1.0.0', principal:'fixture-a', domain:'fixture-numbers',
  sourcePin:pin, ...patch
});
const code = (run, expected) => assert.throws(run, e => e.code === expected);
const noExecution = result => {
  assert.equal(result.executed,false);
  assert.equal(result.acknowledged,false);
  assert.equal(result.receipt,null);
};
const syntheticGate = (patch = {}) => ({
  authenticated:true,current:true,taskBound:true,leaseValid:true,revoked:false,
  principal:'fixture-a',domain:'fixture-numbers',handlerPin:pin,...patch
});

test('source provenance: exact imported module bytes, exports and no dispatch', () => {
  const b=readFileSync(new URL('../lib/pinned-capability-recall.mjs',import.meta.url));
  const blob=createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex');
  assert.equal(blob,'3b6078868bcc5c621fd3efb8ebc205f1d4114cf3');
  assert.equal(typeof validate,'function');assert.equal(typeof recall,'function');
  assert.equal(typeof admissionGate,'function');
  console.log('PINNED_RECALL_MODULE_RECEIPT '+JSON.stringify({
    schema:'pinned-recall-direct-module-tests/1', moduleGitBlob:blob,
    moduleSha256:createHash('sha256').update(b).digest('hex'),
    importPath:'../lib/pinned-capability-recall.mjs', copiedImplementation:false,
    networkCalls:0,hostDispatches:0,executionScope:'PUBLIC_UNIT_TEST_ONLY'
  }));
});
test('validate returns the actual complete record',()=>{
  const r=record();assert.equal(validate(r),r);
});
for(const key of ['id','version','principal','domain','input','output','effect','resource','sourcePin','verifier','rollback']){
  test('validate rejects missing, empty and non-string '+key,()=>{
    for(const value of [undefined,null,'',0,false,[]]){
      code(()=>validate(record({[key]:value})),'MISSING_'+key);
    }
  });
}
test('validate rejects malformed semantic versions',()=>{
  for(const version of ['1','1.0','v1.0.0','1.0.0-beta','1.a.0',' 1.0.0'])
    code(()=>validate(record({version})),'BAD_VERSION');
});
test('validate rejects malformed source pins',()=>{
  for(const sourcePin of ['abc','A'.repeat(64),'g'.repeat(64),'a'.repeat(63),'a'.repeat(65)])
    code(()=>validate(record({sourcePin})),'BAD_PIN');
});
test('validate rejects malformed aliases and accepts empty alias set',()=>{
  for(const aliases of [undefined,null,'sum',[''],[1],['sum',null]])
    code(()=>validate(record({aliases})),'BAD_ALIASES');
  assert.equal(validate(record({aliases:[]})).aliases.length,0);
});
test('recall requires a nonempty string name',()=>{
  for(const q of [undefined,null,{},query({name:''}),query({name:1})])
    code(()=>recall([record()],q),'NAME_REQUIRED');
});
for(const key of ['version','principal','domain','sourcePin']){
  test('recall requires query field '+key,()=>{
    for(const value of [undefined,null,'',0,false])
      code(()=>recall([record()],query({[key]:value})),'QUERY_'+key);
  });
}
test('exact ID and alias produce the same pinned identity',()=>{
  assert.deepEqual(recall([record()],query({name:'public.sum'})),recall([record()],query()));
});
test('unknown name and absent exact identity are separate failures',()=>{
  code(()=>recall([record()],query({name:'other'})),'UNKNOWN_CAPABILITY');
  for(const patch of [{version:'9.0.0'},{principal:'fixture-b'},{domain:'fixture-other'}])
    code(()=>recall([record()],query(patch)),'EXACT_VERSION_PRINCIPAL_DOMAIN_MISSING');
});
test('multiple versions do not force largest-version selection',()=>{
  const rows=[record({version:'99.0.0'}),record()];
  assert.equal(recall(rows,query()).version,'1.0.0');
});
test('same alias across principals and domains remains separated',()=>{
  const rows=[record({principal:'fixture-b'}),record({domain:'fixture-other'}),record()];
  assert.equal(recall(rows,query()).principal,'fixture-a');
  assert.equal(recall(rows,query()).domain,'fixture-numbers');
});
test('duplicate exact identities fail even when one pin matches',()=>{
  code(()=>recall([record(),record()],query()),'AMBIGUOUS_EXACT_MATCH');
  code(()=>recall([record(),record({sourcePin:'b'.repeat(64)})],query()),'AMBIGUOUS_EXACT_MATCH');
});
test('selected record must have the requested source pin',()=>{
  code(()=>recall([record()],query({sourcePin:'b'.repeat(64)})),'PIN_MISMATCH');
});
test('selected malformed contract fails; unrelated malformed rows do not block recall',()=>{
  code(()=>recall([record({verifier:''})],query()),'MISSING_verifier');
  assert.equal(recall([null,{}, {id:'other',aliases:null},record()],query()).id,'public.sum');
});
test('historical success survives unavailable route without authority',()=>{
  const result=recall([record({route:'DOWN'})],query());
  assert.equal(result.history,'PASS_SCOPED');assert.equal(result.route,'DOWN');
  assert.equal(result.admission,'NOT_ESTABLISHED_BY_RECALL');assert.equal(result.receipt,null);
});
test('unknown history and route are not upgraded',()=>{
  const r=record();delete r.history;delete r.route;
  const out=recall([r],query());assert.equal(out.history,'UNKNOWN');assert.equal(out.route,'UNKNOWN');
});
test('identity digest binds ID, version, principal, domain and source pin',()=>{
  const r=record(), out=recall([r],query());
  const expected=createHash('sha256').update(JSON.stringify([r.id,r.version,r.principal,r.domain,r.sourcePin])).digest('hex');
  assert.equal(out.identityHash,expected);
});
test('catalog order and 24 exact version/principal/domain combinations preserve selection',()=>{
  const versions=['1.0.0','2.0.0','3.0.0','99.0.0'];
  const principals=['fixture-a','fixture-b','fixture-c'], domains=['fixture-numbers','fixture-words'];
  const rows=versions.flatMap(version=>principals.flatMap(principal=>domains.map(domain=>record({version,principal,domain}))));
  for(const c of rows){
    const q=query({version:c.version,principal:c.principal,domain:c.domain});
    assert.equal(recall(rows,q).identityHash,recall([...rows].reverse(),q).identityHash);
    const out=recall(rows,q);
    assert.deepEqual([out.version,out.principal,out.domain],[c.version,c.principal,c.domain]);
  }
});
test('gate rejects missing or non-recall records',()=>{
  for(const r of [undefined,null,{}, {admission:'EXECUTED'}])
    code(()=>admissionGate(r,syntheticGate()),'RECALL_REQUIRED');
});
test('absent separate gate stays on hold',()=>{
  const r=recall([record()],query());
  for(const g of [undefined,null,{}]){
    const out=admissionGate(r,g);assert.equal(out.state,'HOLD_ADMISSION');noExecution(out);
  }
});
for(const field of ['authenticated','current','taskBound','leaseValid']){
  test('gate requires exact boolean true for '+field,()=>{
    const r=recall([record()],query());
    for(const v of [undefined,null,false,'true',1]){
      const out=admissionGate(r,syntheticGate({[field]:v}));
      assert.equal(out.state,'HOLD_ADMISSION');noExecution(out);
    }
  });
}
test('revocation must be explicitly false',()=>{
  const r=recall([record()],query());
  for(const revoked of [undefined,null,true,'false',0]){
    const out=admissionGate(r,syntheticGate({revoked}));assert.equal(out.state,'HOLD_ADMISSION');noExecution(out);
  }
});
for(const [field,value] of [['principal','fixture-other'],['domain','fixture-other'],['handlerPin','b'.repeat(64)]]){
  test('gate rejects mismatched '+field,()=>{
    const out=admissionGate(recall([record()],query()),syntheticGate({[field]:value}));
    assert.equal(out.state,'HOLD_ADMISSION');noExecution(out);
  });
}
test('synthetic complete gate is eligibility only, never executor acknowledgment',()=>{
  const out=admissionGate(recall([record()],query()),syntheticGate());
  assert.equal(out.state,'HOST_DISPATCH_ELIGIBLE_ONLY');noExecution(out);
});
test('read-only recall leaves caller catalog and query unchanged',()=>{
  const r=Object.freeze(record({aliases:Object.freeze(['sum'])}));
  const rows=Object.freeze([r]),q=Object.freeze(query()),before=JSON.stringify([rows,q]);
  recall(rows,q);assert.equal(JSON.stringify([rows,q]),before);
});
