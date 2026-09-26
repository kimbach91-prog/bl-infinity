import test from 'node:test';
import assert from 'node:assert/strict';
import {TrustCaseRuntime} from './index.mjs';

function rt(){
  let now=Date.parse('2026-09-27T00:00:00Z');
  const r=new TrustCaseRuntime({now:()=>now,default_sla_hours:24});
  return {r,setNow:(x)=>{now=Date.parse(x);}};
}

test('cross-tenant case access is denied',()=>{
  const {r}=rt();
  r.createCase({case_id:'c1',tenant_id:'t1',category:'DISPUTE',opened_by:'u1',subject_ref:'job://1'});
  assert.throws(()=>r.getForTenant('c1','t2'),/CROSS_TENANT_CASE_DENIED/);
});

test('reviewer must be independent from opener',()=>{
  const {r}=rt();
  r.createCase({case_id:'c1',tenant_id:'t1',category:'ABUSE',opened_by:'u1',subject_ref:'acct://x'});
  assert.throws(()=>r.assignReviewer({case_id:'c1',tenant_id:'t1',reviewer_id:'u1'}),/SEPARATION_OF_DUTIES_VIOLATION/);
  assert.equal(r.assignReviewer({case_id:'c1',tenant_id:'t1',reviewer_id:'u2'}).state,'UNDER_REVIEW');
});

test('decision requires assigned reviewer and preserves evidence refs',()=>{
  const {r}=rt();
  r.createCase({case_id:'c1',tenant_id:'t1',category:'POLICY',opened_by:'u1',subject_ref:'artifact://1',evidence_refs:['rcp://1']});
  r.assignReviewer({case_id:'c1',tenant_id:'t1',reviewer_id:'u2'});
  const d=r.decide({
    decision_id:'d1',case_id:'c1',tenant_id:'t1',reviewer_id:'u2',
    outcome:'allow',rationale:'policy satisfied',policy_ref:'policy://v1',evidence_refs:['rcp://2']
  });
  assert.deepEqual(d.evidence_refs,['rcp://1','rcp://2']);
  assert.equal(r.getForTenant('c1','t1').state,'DECIDED');
});

test('appeal creates a new case linked to original decision',()=>{
  const {r}=rt();
  r.createCase({case_id:'c1',tenant_id:'t1',category:'DISPUTE',opened_by:'u1',subject_ref:'job://1'});
  r.assignReviewer({case_id:'c1',tenant_id:'t1',reviewer_id:'u2'});
  r.decide({decision_id:'d1',case_id:'c1',tenant_id:'t1',reviewer_id:'u2',outcome:'deny',rationale:'x',policy_ref:'p://1'});
  const a=r.appeal({appeal_case_id:'a1',case_id:'c1',tenant_id:'t1',opened_by:'u1',reason:'new evidence'});
  assert.equal(a.parent_case_id,'c1');
  assert.equal(a.metadata.appealed_decision_id,'d1');
  assert.equal(r.getForTenant('c1','t1').state,'APPEALED');
});

test('supersession preserves old decision as immutable history',()=>{
  const {r}=rt();
  r.createCase({case_id:'c1',tenant_id:'t1',category:'POLICY',opened_by:'u1',subject_ref:'x'});
  r.assignReviewer({case_id:'c1',tenant_id:'t1',reviewer_id:'u2'});
  r.decide({decision_id:'d1',case_id:'c1',tenant_id:'t1',reviewer_id:'u2',outcome:'deny',rationale:'old',policy_ref:'p://1'});
  const d2=r.supersedeDecision({old_decision_id:'d1',new_decision_id:'d2',case_id:'c1',tenant_id:'t1',reviewer_id:'u2',outcome:'allow',rationale:'corrected',policy_ref:'p://2'});
  assert.equal(d2.supersedes,'d1');
  assert.equal(r.decisions.get('d1').superseded_by,'d2');
  assert.equal(r.decisions.get('d1').rationale,'old');
});

test('SLA overdue is visible for unresolved case',()=>{
  const {r,setNow}=rt();
  r.createCase({case_id:'c1',tenant_id:'t1',category:'BILLING',opened_by:'u1',subject_ref:'invoice://1'});
  setNow('2026-09-28T01:00:00Z');
  assert.equal(r.slaStatus({case_id:'c1',tenant_id:'t1'}).overdue,true);
});

test('audit export is hash-addressed and contains event lineage',()=>{
  const {r}=rt();
  r.createCase({case_id:'c1',tenant_id:'t1',category:'ACCESS',opened_by:'u1',subject_ref:'acct://1'});
  r.assignReviewer({case_id:'c1',tenant_id:'t1',reviewer_id:'u2'});
  const x=r.exportAudit({case_id:'c1',tenant_id:'t1'});
  assert.ok(x.events.length>=2);
  assert.equal(x.audit_digest.length,64);
});
