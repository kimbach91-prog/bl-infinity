#!/usr/bin/env python3
"""R228: pre-action completion-veto gate for R227 coarse local-target residuals.

Falsifier: R227 adds 342/346 exact heldout predictions but 4 are wrong. Three
wrong examples are actual level-completion transitions; local recolor cannot
render a scene reset. R217/R218 goal-manifold vetoes miss them because those
models are prediction/render oriented and require learned virtual-goal support.

R228 changes only the discriminating mechanism: learn a conservative
PRE-ACTION completion classifier from p0-p9 public traces, independent of R227
heldout outcomes. Candidate families are fit on p0-p4 and selected on p5-p9 by:
  1) zero false-positive completion vetoes,
  2) maximum correctly detected completion events,
  3) higher distinct-trace support, then lower predefined complexity.
The selected family is refit on p0-p9. It may only ABSTAIN an R227 candidate;
it never fabricates a next scene. R225 precedence and R227 target model remain
unchanged. p10-p19 is evaluated once after freezing selection/refit.

PUBLIC_OFFLINE research only; no independent-generalization/Kaggle-score claim.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_low_confidence_goal_manifold_veto_225 as r225
import public_ft09_coarse_local_target_gate_227 as r227

RUNG=228
GAME='ft09-0d8bbf25'
FAMILIES=('macro6_pos','colorhist_pos','macro6_local','colorhist_local','quadrant_pos','rowcol_pos','component_pos')
SUPPORTS=(2,3,4)
COMPLEXITY={f:i for i,f in enumerate(FAMILIES)}

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board): return [row[:] for row in board[:-1]]

def prekey(fam,r,lm):
    lvl=int(lm['level_before']) if lm else -1
    r0,c0,_,_,_=r['bbox']; pos=(r0//8,c0//8)
    cur,_,_=r['base']; local=r227.feat('current_ring2hist',r,lm)
    if fam=='macro6_pos': return (lvl,pos,r218.macro6_hist(r['before']))
    if fam=='colorhist_pos': return (lvl,pos,r218.color_hist(r['before']))
    if fam=='macro6_local': return (lvl,cur,local,r218.macro6_hist(r['before']))
    if fam=='colorhist_local': return (lvl,cur,local,r218.color_hist(r['before']))
    if fam=='quadrant_pos': return (lvl,pos,r218.quadrant_hist(r['before']))
    if fam=='rowcol_pos': return (lvl,pos,r218.rowcol_bands(r['before']))
    if fam=='component_pos': return (lvl,pos,r218.component_spectrum(r['before']))
    raise KeyError(fam)

def fit_veto(paths,fam,min_traces):
    obs=defaultdict(lambda:{'labels':Counter(),'traces':defaultdict(set)})
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            lm=meta.get(r['step0'])
            if lm is None: continue
            completion=bool(lm['level_after']>lm['level_before'])
            k=repr(prekey(fam,r,lm));x=obs[k]
            x['labels'][completion]+=1;x['traces'][completion].add(r['path'])
    model=set();rej=Counter()
    for k,x in obs.items():
        if x['labels'][False]: rej['noncompletion_collision']+=1;continue
        if not x['labels'][True]: rej['no_completion']+=1;continue
        if len(x['traces'][True])<min_traces: rej['low_trace_support']+=1;continue
        model.add(k)
    return model,rej

def eval_veto(paths,model,fam):
    s=Counter();examples=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            lm=meta.get(r['step0'])
            if lm is None: continue
            actual=bool(lm['level_after']>lm['level_before'])
            pred=repr(prekey(fam,r,lm)) in model
            s['eligible']+=1;s['actual_completion' if actual else 'actual_noncompletion']+=1
            if pred:
                s['veto_predictions']+=1
                s['true_positive' if actual else 'false_positive']+=1
                if len(examples)<30: examples.append({'p':r['p'],'step0':r['step0'],'action':r['action'],'actual_completion':actual,'level_before':lm['level_before'],'level_after':lm['level_after']})
            elif actual: s['false_negative']+=1
    return {**dict(s),'examples':examples}

def select(train5,val5):
    cand={}
    for fam in FAMILIES:
        for sup in SUPPORTS:
            m,rej=fit_veto(train5,fam,sup);v=eval_veto(val5,m,fam)
            cand[f'{fam}|t{sup}']={'family':fam,'min_traces':sup,'keys':len(m),'rejected':dict(rej),'validation':v}
    safe=[(k,v) for k,v in cand.items() if v['validation'].get('veto_predictions',0)>0 and v['validation'].get('false_positive',0)==0]
    if not safe:return None,cand
    safe.sort(key=lambda kv:(-kv[1]['validation'].get('true_positive',0),-kv[1]['min_traces'],COMPLEXITY[kv[1]['family']],kv[1]['validation'].get('veto_predictions',0)))
    return safe[0][0],cand

def incumbent_and_candidate(r,lm,m,tab,fam):
    pred,_=r221.r218_predict(r,lm,m)
    if pred is None: pred,_=r221.r219_predict(r,lm,m)
    if pred is None: pred,_,_=r225.lowbase_goal_veto(r,lm,m)
    if pred is not None:return 'incumbent',None,None
    tgt=tab.get(repr(r227.feat(fam,r,lm)))
    if tgt is None:return 'abstain',None,None
    veto=r227.goal_veto(r,lm,tgt,m)
    if veto is not None:return 'abstain',None,veto
    pred=gp(r212.recolor_bbox(r['before'],r['bbox'],tgt))
    return 'candidate',pred,None

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train5,val5,train,held=ps[:5],ps[5:10],ps[:10],ps[10:]

    selected227,c227=r227.select(train5,val5)
    if selected227 is None:raise RuntimeError('R227 selection unexpectedly absent')
    cfg227=c227[selected227];fam227=cfg227['family'];sup227=cfg227['min_traces']
    tab,_=r227.fit(train,fam227,sup227);m=r221.build_models(train)

    selected,candidates=select(train5,val5)
    if selected is None:
        return {'schema':'deus/arc3-ft09-preaction-completion-veto/1','rung':RUNG,'game':GAME,
          'r227_selected':selected227,'selection':{'selected':None,'candidates':candidates},'heldout':None,
          'zero_wrong_coverage_gain_gate_pass':False,'promotion':{'coverage_expert_promotion':False,'solver_promotion':False,'kaggle_packaging':False},'truth':truth()}
    cfg=candidates[selected];fam=cfg['family'];sup=cfg['min_traces']
    veto_model,rej=fit_veto(train,fam,sup)

    s=Counter();veto_examples=[];wrong=[];added=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            stage,pred,_=incumbent_and_candidate(r,lm,m,tab,fam227)
            if stage=='incumbent':s['incumbent_predictions']+=1;continue
            if stage!='candidate':s['abstain']+=1;continue
            is_veto=repr(prekey(fam,r,lm)) in veto_model
            if is_veto:
                s['completion_vetoes']+=1;s['abstain']+=1
                actual_completion=bool(lm and lm['level_after']>lm['level_before'])
                s['veto_true_completion' if actual_completion else 'veto_false_noncompletion']+=1
                if len(veto_examples)<40:veto_examples.append({'p':r['p'],'step0':r['step0'],'action':r['action'],'actual_completion':actual_completion,'level_before':lm['level_before'] if lm else None,'level_after':lm['level_after'] if lm else None})
                continue
            ok=pred==gp(r['after']);s['candidate_predictions']+=1;s['candidate_correct' if ok else 'candidate_wrong']+=1
            if len(added)<80:added.append({'p':r['p'],'step0':r['step0'],'action':r['action'],'correct':ok,'level_before':lm['level_before'] if lm else None,'level_after':lm['level_after'] if lm else None})
            if not ok and len(wrong)<40:wrong.append({'p':r['p'],'step0':r['step0'],'action':r['action'],'level_before':lm['level_before'] if lm else None,'level_after':lm['level_after'] if lm else None})
    assert s['eligible']==914,dict(s);assert s['incumbent_predictions']==307,dict(s)
    cp=s['candidate_predictions'];cc=s['candidate_correct'];cw=s['candidate_wrong']
    total=307+cc if cw==0 else 307;gate=bool(cp>0 and cw==0 and cc==cp and total>307)
    held={**dict(s),'candidate_accuracy':round(cc/cp,6) if cp else None,'union_exact_if_zero_wrong':total,
      'union_coverage_if_zero_wrong':round(total/914,6) if gate else round(307/914,6),'veto_examples':veto_examples,'added_examples':added,'wrong_examples':wrong}
    return {'schema':'deus/arc3-ft09-preaction-completion-veto/1','rung':RUNG,'game':GAME,'r227_selected':selected227,
      'selection':{'protocol':'fit completion-only preaction keys p0-p4; validate p5-p9 zero false-positive; maximize completion TP','selected':selected,'selected_config':cfg,'candidates':candidates},
      'refit':{'paths':'p0-p9','family':fam,'min_traces':sup,'keys':len(veto_model),'rejected':dict(rej)},'heldout':held,'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False,'next_gate':'if one residual remains, inspect only that mismatch class; if zero-wrong gain, freeze completion-veto before R227 local render'},'truth':truth()}

def truth():
    return {'public_trace_only':True,'completion_veto_fit_p0_p4_validate_p5_p9_only':True,'selected_veto_refit_p0_p9_only':True,
      'veto_uses_preaction_state_only':True,'veto_can_only_abstain':True,'r225_precedence_preserved':True,'r227_target_model_unchanged':True,
      'heldout_never_updates_models_or_selection':True,'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'r227':d['r227_selected'],'selection':d['selection'].get('selected'),'selected_config':d['selection'].get('selected_config'),'refit':d.get('refit'),'heldout':d.get('heldout'),'gate':d.get('zero_wrong_coverage_gain_gate_pass',False)},sort_keys=True))
if __name__=='__main__':main()
