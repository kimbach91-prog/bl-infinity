import crypto from 'node:crypto';

export const CASE_STATES = Object.freeze(['OPEN','UNDER_REVIEW','DECIDED','APPEALED','CLOSED']);
export const CASE_CATEGORIES = Object.freeze(['ABUSE','DISPUTE','APPEAL','POLICY','BILLING','DATA','ACCESS']);

function req(v,n){ if(typeof v!=='string'||!v.trim()) throw new Error(`INVALID_${n}`); return v.trim(); }
function iso(v,n){ const d=new Date(v); if(!Number.isFinite(d.getTime())) throw new Error(`INVALID_${n}`); return d.toISOString(); }
function sha(v){ return crypto.createHash('sha256').update(typeof v==='string'?v:JSON.stringify(v)).digest('hex'); }

export class TrustCaseRuntime {
  constructor({now=()=>Date.now(), default_sla_hours=72}={}){
    this.now=now;
    this.default_sla_hours=Number(default_sla_hours);
    this.cases=new Map();
    this.decisions=new Map();
    this.events=[];
  }

  createCase({
    case_id, tenant_id, category, opened_by, subject_ref,
    evidence_refs=[], severity='NORMAL', sla_hours=null, metadata={}
  }){
    const id=req(case_id,'CASE_ID');
    if(this.cases.has(id)) throw new Error('CASE_EXISTS');
    const cat=req(category,'CATEGORY').toUpperCase();
    if(!CASE_CATEGORIES.includes(cat)) throw new Error('CATEGORY_NOT_ALLOWED');
    const openedAt=new Date(this.now()).toISOString();
    const sla=Number(sla_hours??this.default_sla_hours);
    if(!Number.isFinite(sla)||sla<=0) throw new Error('INVALID_SLA');
    const row=Object.freeze({
      case_id:id,
      tenant_id:req(tenant_id,'TENANT_ID'),
      category:cat,
      opened_by:req(opened_by,'OPENED_BY'),
      subject_ref:req(subject_ref,'SUBJECT_REF'),
      evidence_refs:Object.freeze([...new Set(evidence_refs.map(x=>req(x,'EVIDENCE_REF')))]),
      severity:req(severity,'SEVERITY').toUpperCase(),
      state:'OPEN',
      opened_at:openedAt,
      due_at:new Date(new Date(openedAt).getTime()+sla*3600000).toISOString(),
      reviewer_id:null,
      latest_decision_id:null,
      parent_case_id:null,
      metadata:Object.freeze({...metadata})
    });
    this.cases.set(id,row);
    this._event('CASE_OPENED',row,{});
    return row;
  }

  _event(type,row,details){
    const e=Object.freeze({
      event_id:`case-event-${this.events.length+1}`,
      type,
      case_id:row.case_id,
      tenant_id:row.tenant_id,
      at:new Date(this.now()).toISOString(),
      details:Object.freeze({...details})
    });
    this.events.push(e);
    return e;
  }

  getForTenant(case_id,tenant_id){
    const row=this.cases.get(req(case_id,'CASE_ID'));
    if(!row) throw new Error('CASE_NOT_FOUND');
    if(row.tenant_id!==req(tenant_id,'TENANT_ID')) throw new Error('CROSS_TENANT_CASE_DENIED');
    return row;
  }

  assignReviewer({case_id,tenant_id,reviewer_id}){
    const row=this.getForTenant(case_id,tenant_id);
    const reviewer=req(reviewer_id,'REVIEWER_ID');
    if(reviewer===row.opened_by) throw new Error('SEPARATION_OF_DUTIES_VIOLATION');
    const updated=Object.freeze({...row,reviewer_id:reviewer,state:'UNDER_REVIEW'});
    this.cases.set(row.case_id,updated);
    this._event('REVIEWER_ASSIGNED',updated,{reviewer_id:reviewer});
    return updated;
  }

  decide({
    decision_id, case_id, tenant_id, reviewer_id, outcome,
    rationale, policy_ref, evidence_refs=[], effect_ref=null
  }){
    const did=req(decision_id,'DECISION_ID');
    if(this.decisions.has(did)) throw new Error('DECISION_EXISTS');
    const row=this.getForTenant(case_id,tenant_id);
    const reviewer=req(reviewer_id,'REVIEWER_ID');
    if(row.reviewer_id!==reviewer) throw new Error('REVIEWER_MISMATCH');
    if(reviewer===row.opened_by) throw new Error('SEPARATION_OF_DUTIES_VIOLATION');
    const decision=Object.freeze({
      decision_id:did,
      case_id:row.case_id,
      tenant_id:row.tenant_id,
      reviewer_id:reviewer,
      outcome:req(outcome,'OUTCOME').toUpperCase(),
      rationale:req(rationale,'RATIONALE'),
      policy_ref:req(policy_ref,'POLICY_REF'),
      evidence_refs:Object.freeze([...new Set([...row.evidence_refs,...evidence_refs.map(x=>req(x,'EVIDENCE_REF'))])]),
      evidence_digest:sha([...row.evidence_refs,...evidence_refs]),
      effect_ref:effect_ref?req(effect_ref,'EFFECT_REF'):null,
      decided_at:new Date(this.now()).toISOString(),
      supersedes:null,
      superseded_by:null
    });
    this.decisions.set(did,decision);
    const updated=Object.freeze({...row,state:'DECIDED',latest_decision_id:did});
    this.cases.set(row.case_id,updated);
    this._event('DECISION_RECORDED',updated,{decision_id:did,outcome:decision.outcome});
    return decision;
  }

  appeal({
    appeal_case_id, case_id, tenant_id, opened_by, reason, evidence_refs=[]
  }){
    const original=this.getForTenant(case_id,tenant_id);
    if(!original.latest_decision_id) throw new Error('NO_DECISION_TO_APPEAL');
    const id=req(appeal_case_id,'APPEAL_CASE_ID');
    if(this.cases.has(id)) throw new Error('CASE_EXISTS');
    const openedAt=new Date(this.now()).toISOString();
    const appeal=Object.freeze({
      case_id:id,
      tenant_id:original.tenant_id,
      category:'APPEAL',
      opened_by:req(opened_by,'OPENED_BY'),
      subject_ref:original.subject_ref,
      evidence_refs:Object.freeze([...new Set([...original.evidence_refs,...evidence_refs.map(x=>req(x,'EVIDENCE_REF'))])]),
      severity:original.severity,
      state:'OPEN',
      opened_at:openedAt,
      due_at:new Date(new Date(openedAt).getTime()+this.default_sla_hours*3600000).toISOString(),
      reviewer_id:null,
      latest_decision_id:null,
      parent_case_id:original.case_id,
      metadata:Object.freeze({reason:req(reason,'APPEAL_REASON'), appealed_decision_id:original.latest_decision_id})
    });
    this.cases.set(id,appeal);
    const originalUpdated=Object.freeze({...original,state:'APPEALED'});
    this.cases.set(original.case_id,originalUpdated);
    this._event('APPEAL_OPENED',appeal,{parent_case_id:original.case_id,appealed_decision_id:original.latest_decision_id});
    return appeal;
  }

  supersedeDecision({
    old_decision_id,new_decision_id,case_id,tenant_id,reviewer_id,outcome,rationale,policy_ref,evidence_refs=[]
  }){
    const old=this.decisions.get(req(old_decision_id,'OLD_DECISION_ID'));
    if(!old) throw new Error('OLD_DECISION_NOT_FOUND');
    const next=this.decide({
      decision_id:new_decision_id,case_id,tenant_id,reviewer_id,outcome,rationale,policy_ref,evidence_refs
    });
    const oldUpdated=Object.freeze({...old,superseded_by:next.decision_id});
    const nextUpdated=Object.freeze({...next,supersedes:old.decision_id});
    this.decisions.set(old.decision_id,oldUpdated);
    this.decisions.set(next.decision_id,nextUpdated);
    return nextUpdated;
  }

  close({case_id,tenant_id,authority_ref}){
    const row=this.getForTenant(case_id,tenant_id);
    req(authority_ref,'AUTHORITY_REF');
    const updated=Object.freeze({...row,state:'CLOSED'});
    this.cases.set(row.case_id,updated);
    this._event('CASE_CLOSED',updated,{authority_ref});
    return updated;
  }

  slaStatus({case_id,tenant_id,at=null}){
    const row=this.getForTenant(case_id,tenant_id);
    const now=at?new Date(iso(at,'AT')).getTime():this.now();
    return Object.freeze({
      case_id:row.case_id,
      state:row.state,
      due_at:row.due_at,
      overdue:!['CLOSED','DECIDED'].includes(row.state)&&now>new Date(row.due_at).getTime()
    });
  }

  exportAudit({case_id,tenant_id}){
    const row=this.getForTenant(case_id,tenant_id);
    const decisions=[...this.decisions.values()].filter(d=>d.case_id===row.case_id);
    const events=this.events.filter(e=>e.case_id===row.case_id);
    return Object.freeze({
      case:row,
      decisions:Object.freeze(decisions),
      events:Object.freeze(events),
      audit_digest:sha({row,decisions,events})
    });
  }
}
