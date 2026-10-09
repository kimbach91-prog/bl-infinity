// Public reference acceptance tests. No production adapter, grant or private data.
// SQLite single-host atomicity is not distributed consensus or external exactly-once.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { performance } from 'node:perf_hooks';
const SELF=fileURLToPath(import.meta.url);
const sha=x=>createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const WEIGHTS=[1,3,5,7,11,13,17,19];
const PIN=sha('public-bounded-weighted-integer-sum/v1|'+WEIGHTS.join(','));
const fail=code=>{throw Object.assign(new Error(code),{code});};
const contract=()=>({id:'public.weighted-sum',version:'1.0.0',aliases:['weighted-sum'],
  principal:'public-fixture',input:'bounded-int[8]',output:'decimal-int',domain:'public-fixture',
  effect:'transaction-local-only',resource:'one-local-process',programPin:PIN,
  verifier:'sqlite-integer-dot-product/v1',rollback:'discard-isolated-test-db',
  history:'PASS_SCOPED_FIXTURE',route:'AVAILABLE_FIXTURE_ONLY'});
function validate(c){
  for(const key of ['id','version','principal','input','output','domain','effect','resource','programPin','verifier','rollback'])
    if(typeof c?.[key]!=='string'||!c[key])fail('MISSING_CONTRACT_'+key);
  if(!/^\d+\.\d+\.\d+$/.test(c.version))fail('BAD_VERSION');
  if(!/^[a-f0-9]{64}$/.test(c.programPin))fail('BAD_SOURCE_PIN');
  if(!Array.isArray(c.aliases)||c.aliases.some(x=>typeof x!=='string'||!x))fail('BAD_ALIASES');
  return c;
}
function recall(records,request){
  records.forEach(validate);
  const matches=records.filter(c=>c.id===request.name||c.aliases.includes(request.name));
  if(matches.length!==1)fail(matches.length?'AMBIGUOUS_RECALL':'UNKNOWN_CAPABILITY');
  const c=matches[0];
  if(c.version!==request.version)fail('STALE_VERSION');
  if(c.principal!==request.principal)fail('PRINCIPAL_MISMATCH');
  if(c.programPin!==request.programPin)fail('SOURCE_PIN_MISMATCH');
  return {contract:c,state:c.route==='AVAILABLE_FIXTURE_ONLY'?'CANDIDATE_NOT_AUTHORITY':'HOLD_CURRENT_ROUTE',historical:c.history};
}
function packet(i){return {jobId:'fixture-'+i,version:'1.0.0',programPin:PIN,principal:'public-fixture',
  values:WEIGHTS.map((_,j)=>((i+1)*(j+3)*7919)%200001-100000)};}
function exact(values){let n=0n;for(let i=0;i<8;i++)n+=BigInt(values[i])*BigInt(WEIGHTS[i]);return n.toString();}
function checkPacket(p){
  if(!p||typeof p.jobId!=='string'||!/^fixture-[A-Za-z0-9_-]{1,48}$/.test(p.jobId))fail('BAD_JOB_ID');
  if(p.version!=='1.0.0'||p.programPin!==PIN||p.principal!=='public-fixture')fail('PACKET_CONTRACT_MISMATCH');
  if(!Array.isArray(p.values)||p.values.length!==8||p.values.some(v=>!Number.isSafeInteger(v)||Math.abs(v)>100000))fail('INPUT_DOMAIN');
}
function open(path){
  const db=new DatabaseSync(path);db.exec('PRAGMA busy_timeout=5000; PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS receipts(job TEXT PRIMARY KEY, input_hash TEXT NOT NULL, output TEXT NOT NULL, output_hash TEXT NOT NULL, effects INTEGER NOT NULL CHECK(effects=1));');return db;
}
// All effects are contained in one local SQLite transaction. No network/external effects.
function execute(path,p,crash='none'){
  checkPacket(p);const expected=exact(p.values),inputHash=sha(p),db=open(path);
  try{
    db.exec('BEGIN IMMEDIATE');
    const prior=db.prepare('SELECT * FROM receipts WHERE job=?').get(p.jobId);
    if(prior){
      if(prior.input_hash!==inputHash)fail('DUPLICATE_JOB_DIFFERENT_INPUT');
      if(prior.output!==expected||prior.output_hash!==sha(expected)||prior.effects!==1)fail('RECEIPT_TAMPER');
      db.exec('COMMIT');return {state:'REUSED_VERIFIED',job:p.jobId,inputHash,output:prior.output,outputHash:prior.output_hash,effects:1};
    }
    // Independent arithmetic implementation: SQLite integer multiplications plus sum.
    const terms=p.values.map((_,i)=>'? * '+WEIGHTS[i]).join(' + ');
    const oracle=db.prepare('SELECT '+terms+' AS n').get(...p.values).n.toString();
    if(oracle!==expected)fail('ORACLE_MISMATCH');
    db.prepare('INSERT INTO receipts VALUES(?,?,?,?,1)').run(p.jobId,inputHash,expected,sha(expected));
    if(crash==='before-commit')process.exit(86);
    db.exec('COMMIT');
    if(crash==='after-commit')process.exit(87);
    const row=db.prepare('SELECT * FROM receipts WHERE job=?').get(p.jobId);
    if(row.output!==oracle||row.input_hash!==inputHash||row.output_hash!==sha(oracle)||row.effects!==1)fail('READBACK_MISMATCH');
    return {state:'EXECUTED_VERIFIED_LOCAL',job:p.jobId,inputHash,output:oracle,outputHash:row.output_hash,effects:1};
  }finally{db.close();}
}
function child(path,p,crash='none'){
  const r=spawnSync(process.execPath,[SELF,'--fixture-worker',path,JSON.stringify(p),crash],{encoding:'utf8',timeout:10000,maxBuffer:65536});
  if(r.error)throw r.error;
  return r;
}
const request={name:'weighted-sum',version:'1.0.0',principal:'public-fixture',programPin:PIN};
if(process.argv[2]==='--fixture-worker'){
  try{const t=performance.now(),cpu=process.cpuUsage();const r=execute(process.argv[3],JSON.parse(process.argv[4]),process.argv[5]);
    console.log(JSON.stringify({receipt:r,wallMs:performance.now()-t,cpuMicros:process.cpuUsage(cpu),maxRssKiB:process.resourceUsage().maxRSS}));
  }catch(e){console.error(e.code||e.message);process.exitCode=2;}
}else{
  test('complete typed contract and exact pinned recall',()=>{assert.equal(recall([contract()],request).state,'CANDIDATE_NOT_AUTHORITY');});
  for(const field of ['id','version','principal','input','output','domain','effect','resource','programPin','verifier','rollback']){
    test('missing required contract field: '+field,()=>{const c=contract();delete c[field];assert.throws(()=>validate(c),new RegExp('MISSING_CONTRACT_'+field));});
  }
  test('unknown alias and ambiguous alias cannot choose the largest version',()=>{
    assert.throws(()=>recall([contract()],{...request,name:'missing'}),/UNKNOWN_CAPABILITY/);
    assert.throws(()=>recall([contract(),{...contract(),id:'another',version:'99.0.0'}],request),/AMBIGUOUS_RECALL/);
  });
  for(const [field,value,code] of [['version','0.0.1','STALE_VERSION'],['principal','another-owner','PRINCIPAL_MISMATCH'],['programPin','f'.repeat(64),'SOURCE_PIN_MISMATCH']]){
    test('recall negative '+field,()=>assert.throws(()=>recall([contract()],{...request,[field]:value}),new RegExp(code)));
  }
  test('past PASS survives unavailable current route without gaining authority',()=>{
    const r=recall([{...contract(),route:'DOWN'}],request);assert.equal(r.historical,'PASS_SCOPED_FIXTURE');assert.equal(r.state,'HOLD_CURRENT_ROUTE');
  });
  test('bounded deterministic computation: 64 frozen fixtures and domain negatives',()=>{
    const dir=mkdtempSync(join(tmpdir(),'public-contract-'));
    try{for(let i=0;i<64;i++){const p=packet(i);assert.equal(execute(join(dir,'a.db'),p).output,exact(p.values));}
      for(const bad of [[1],Array(8).fill(100001),Array(8).fill(1.5),Array(8).fill(NaN)])assert.throws(()=>execute(join(dir,'a.db'),{...packet(99),values:bad}),/INPUT_DOMAIN/);
    }finally{rmSync(dir,{recursive:true,force:true});}
  });
  for(const crash of ['before-commit','after-commit']){
    test('real process interruption '+crash+' and same-job cold resume',()=>{
      const dir=mkdtempSync(join(tmpdir(),'public-resume-')),path=join(dir,'a.db'),p=packet(80);
      try{const r=child(path,p,crash);assert.equal(r.status,crash==='before-commit'?86:87);
        const resumed=child(path,p);assert.equal(resumed.status,0,resumed.stderr);
        const value=JSON.parse(resumed.stdout).receipt;assert.equal(value.output,exact(p.values));
        assert.equal(value.state,crash==='before-commit'?'EXECUTED_VERIFIED_LOCAL':'REUSED_VERIFIED');
        assert.equal(execute(path,p).state,'REUSED_VERIFIED');
        const db=open(path);assert.equal(db.prepare('SELECT COUNT(*) n FROM receipts').get().n,1);assert.equal(db.prepare('SELECT SUM(effects) n FROM receipts').get().n,1);db.close();
      }finally{rmSync(dir,{recursive:true,force:true});}
    });
  }
  test('duplicate changed input and tampered receipt fail closed',()=>{
    const dir=mkdtempSync(join(tmpdir(),'public-neg-')),path=join(dir,'a.db'),p=packet(81);
    try{execute(path,p);assert.throws(()=>execute(path,{...p,values:Array(8).fill(0)}),/DUPLICATE_JOB_DIFFERENT_INPUT/);
      const db=open(path);db.prepare('UPDATE receipts SET output=? WHERE job=?').run('999',p.jobId);db.close();
      assert.throws(()=>execute(path,p),/RECEIPT_TAMPER/);
    }finally{rmSync(dir,{recursive:true,force:true});}
  });
  test('matched DoD: direct vs cold-process lifecycle, identical verified durable outputs',()=>{
    const dir=mkdtempSync(join(tmpdir(),'public-cost-')),direct=[],cold=[],rss=[];
    try{for(let i=0;i<24;i++){
      const p=packet(100+i),a=join(dir,'d'+i+'.db'),b=join(dir,'c'+i+'.db');
      let rd,rc;const d=()=>{const t=performance.now();rd=execute(a,p);direct.push(performance.now()-t);};
      const c=()=>{const t=performance.now(),r=child(b,p);cold.push(performance.now()-t);assert.equal(r.status,0,r.stderr);const out=JSON.parse(r.stdout);rc=out.receipt;rss.push(out.maxRssKiB);};
      if(i%2){c();d();}else{d();c();}assert.deepEqual(rd,rc);
    }
    const stat=a=>{const b=[...a].sort((x,y)=>x-y);return {n:b.length,p50Ms:(b[11]+b[12])/2,p95Ms:b[Math.ceil(b.length*.95)-1],minMs:b[0],maxMs:b.at(-1)};};
    console.log('PUBLIC_CONTRACT_ACCEPTANCE_RECEIPT '+JSON.stringify({schema:'public-contract-acceptance/1',
      executionHost:process.env.GITHUB_ACTIONS==='true'?'GITHUB_ACTIONS_CI':'ISOLATED_LOCAL_PROCESS',node:process.version,
      sourceSha256:sha(readFileSync(SELF,'utf8')),fixtureManifestSha256:sha(Array.from({length:64},(_,i)=>packet(i))),
      fixtureCases:64,lifecyclePairs:24,direct:stat(direct),coldProcess:stat(cold),peakChildRssKiB:Math.max(...rss),
      quality:'ALL_EXACT_AND_DURABLE',recovery:'BEFORE_AND_AFTER_COMMIT_PROCESS_EXIT_TESTED',
      currentRouteAuthority:'NONE_CREATED',newPhysicalBrainCredit:0,externalEffects:0,moneyCost:'NOT_METERED',
      utilityClaim:'OVERHEAD_MEASURED_NO_GENERAL_SPEEDUP_OR_HA_CLAIM'}));
    }finally{rmSync(dir,{recursive:true,force:true});}
  });
}
