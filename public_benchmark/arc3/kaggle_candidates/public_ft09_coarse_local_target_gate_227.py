#!/usr/bin/env python3
"""R227: coarse pre-action local-target gate derived from R226 falsifier.

R226 found 601/607 residual R225 abstentions are clicked-bbox-only outcomes;
532/607 lack a deterministic R221 base key.  The discriminating missing
mechanism is therefore target-color transfer under a coarser representation,
not a new renderer.

Selection protocol is intentionally separate from p10-p19:
  * candidate family/support search: fit p0-p4, validate p5-p9;
  * only zero-wrong exact gameplay-frame candidates may be selected;
  * selected family/support is refit on p0-p9;
  * frozen p10-p19 is evaluated once after unchanged R225 precedence;
  * candidate training keys are admitted only when every training occurrence
    is a clicked-bbox-only transition with the same target color and sufficient
    distinct-trace support.
  * known exact/structural goal manifolds veto candidate local recolors.

No heldout outcome updates any model.  This is PUBLIC_OFFLINE coverage research,
not an independent-generalization or Kaggle-score claim.
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

RUNG=227
GAME='ft09-0d8bbf25'
FAMILIES=(
 'current_four','current_fourhist','current_ring2hist','current_fourhist_ring2hist',
 'current_four_level','current_fourhist_level','current_ring2hist_level',
 'current_fourhist_ring2hist_level','current_pos_level','current_fourhist_pos_level',
 'current_fourhist_run','current_fourhist_level_run',
)
SUPPORTS=(2,3,4,5)

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board): return [row[:] for row in board[:-1]]
def hist(xs): return tuple(sorted(Counter(xs).items()))
def action_class(a): return (a or '').split('(')[0]
def run_bucket(n): return min(int(n or 0),3)

def is_local_only(r):
    b=gp(r['before']); a=gp(r['after']); r0,c0,r1,c1,_=r['bbox']
    anydiff=False
    for rr,(rb,ra) in enumerate(zip(b,a)):
        for cc,(x,y) in enumerate(zip(rb,ra)):
            if x==y: continue
            anydiff=True
            if not (r0<=rr<=r1 and c0<=cc<=c1): return False
    return anydiff

def feat(fam,r,lm):
    cur,four,_global=r['base']; four=tuple(four); ring=tuple(r['ring2'])
    lvl=int(lm['level_before']) if lm else -1
    r0,c0,_,_,_=r['bbox']; pos=(r0//8,c0//8)
    rb=run_bucket(r['run_len'])
    if fam=='current_four': return (cur,four)
    if fam=='current_fourhist': return (cur,hist(four))
    if fam=='current_ring2hist': return (cur,hist(ring))
    if fam=='current_fourhist_ring2hist': return (cur,hist(four),hist(ring))
    if fam=='current_four_level': return (cur,four,lvl)
    if fam=='current_fourhist_level': return (cur,hist(four),lvl)
    if fam=='current_ring2hist_level': return (cur,hist(ring),lvl)
    if fam=='current_fourhist_ring2hist_level': return (cur,hist(four),hist(ring),lvl)
    if fam=='current_pos_level': return (cur,pos,lvl)
    if fam=='current_fourhist_pos_level': return (cur,hist(four),pos,lvl)
    if fam=='current_fourhist_run': return (cur,hist(four),action_class(r['prev_action']),rb)
    if fam=='current_fourhist_level_run': return (cur,hist(four),lvl,action_class(r['prev_action']),rb)
    raise KeyError(fam)

def rows_with_meta(paths):
    out=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if r['eligible']: out.append((r,meta.get(r['step0'])))
    return out

def fit(paths,fam,min_traces):
    obs=defaultdict(lambda:{'labels':Counter(),'traces':defaultdict(set)})
    for r,lm in rows_with_meta(paths):
        k=repr(feat(fam,r,lm))
        if is_local_only(r): label=('local',int(r['target']))
        else: label=('nonlocal',)
        x=obs[k]; x['labels'][label]+=1; x['traces'][label].add(r['path'])
    tab={}; rejected=Counter()
    for k,x in obs.items():
        if len(x['labels'])!=1:
            rejected['label_conflict']+=1; continue
        label=next(iter(x['labels']))
        if label[0]!='local':
            rejected['nonlocal_only']+=1; continue
        if len(x['traces'][label])<min_traces:
            rejected['low_trace_support']+=1; continue
        tab[k]=int(label[1])
    return tab,rejected

def eval_plain(paths,tab,fam):
    s=Counter()
    for r,lm in rows_with_meta(paths):
        s['eligible']+=1
        tgt=tab.get(repr(feat(fam,r,lm)))
        if tgt is None: s['abstain']+=1; continue
        pred=gp(r212.recolor_bbox(r['before'],r['bbox'],tgt))
        s['predictions']+=1
        if pred==gp(r['after']): s['correct']+=1
        else: s['wrong']+=1
    p=s['predictions'];e=s['eligible']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}

def select(train5,val5):
    cand={}
    for fam in FAMILIES:
        for sup in SUPPORTS:
            tab,rej=fit(train5,fam,sup); met=eval_plain(val5,tab,fam)
            cand[f'{fam}|t{sup}']={'family':fam,'min_traces':sup,'keys':len(tab),'rejected':dict(rej),'validation':met}
    zero=[(k,v) for k,v in cand.items() if v['validation'].get('predictions',0)>0 and v['validation'].get('wrong',0)==0]
    if not zero: return None,cand
    # maximize correct/predictions, then prefer higher support and simpler family order
    famrank={f:i for i,f in enumerate(FAMILIES)}
    zero.sort(key=lambda kv:(-kv[1]['validation'].get('correct',0),-kv[1]['validation'].get('predictions',0),-kv[1]['min_traces'],famrank[kv[1]['family']]))
    return zero[0][0],cand

def goal_veto(r,lm,tgt,m):
    virtual=r212.recolor_bbox(r['before'],r['bbox'],tgt)
    if lm is None: return None
    ek=r217.goal_key(lm['level_before'],virtual)
    if ek in m['exact_goal']: return 'exact_goal_manifold'
    sk=r218.structural_key(m['fam'],lm['level_before'],virtual)
    if sk in m['struct_goal']: return 'structural_goal_manifold'
    return None

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    train5=ps[:5]; val5=ps[5:10]; train=ps[:10]; held=ps[10:]
    selected,candidates=select(train5,val5)
    if selected is None:
        return {'schema':'deus/arc3-ft09-coarse-local-target-gate/1','rung':RUNG,'game':GAME,
          'selection':{'selected':None,'candidates':candidates},'heldout':None,
          'promotion':{'coverage_expert_promotion':False,'solver_promotion':False,'kaggle_packaging':False},
          'truth':truth()}
    cfg=candidates[selected];fam=cfg['family'];sup=cfg['min_traces']
    tab,rej=fit(train,fam,sup); m=r221.build_models(train)
    s=Counter();stage=defaultdict(Counter);vetoes=Counter();added=[];wrong=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            pred,_=r221.r218_predict(r,lm,m)
            if pred is None: pred,_=r221.r219_predict(r,lm,m)
            if pred is None: pred,_,_=r225.lowbase_goal_veto(r,lm,m)
            if pred is not None:
                s['incumbent_predictions']+=1
                continue
            tgt=tab.get(repr(feat(fam,r,lm)))
            if tgt is None:
                s['abstain']+=1; continue
            veto=goal_veto(r,lm,tgt,m)
            if veto is not None:
                vetoes[veto]+=1;s['abstain']+=1;continue
            pred=gp(r212.recolor_bbox(r['before'],r['bbox'],tgt))
            ok=pred==gp(r['after'])
            s['candidate_predictions']+=1;s['candidate_correct' if ok else 'candidate_wrong']+=1
            if len(added)<80:
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'correct':ok,'target':tgt,'level':lm['level_before'] if lm else None})
            if not ok and len(wrong)<40:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'target':tgt,'level_before':lm['level_before'] if lm else None,'level_after':lm['level_after'] if lm else None})
    assert s['eligible']==914,dict(s)
    assert s['incumbent_predictions']==307,dict(s)
    cp=s['candidate_predictions'];cw=s['candidate_wrong'];cc=s['candidate_correct']
    total=307+cc if cw==0 else 307
    gate=bool(cp>0 and cw==0 and cc==cp and total>307)
    held={**dict(s),'candidate_accuracy':round(cc/cp,6) if cp else None,
          'union_exact_if_zero_wrong':total,'union_coverage_if_zero_wrong':round(total/914,6) if gate else round(307/914,6),
          'veto_counts':dict(vetoes),'added_examples':added,'wrong_examples':wrong}
    return {'schema':'deus/arc3-ft09-coarse-local-target-gate/1','rung':RUNG,'game':GAME,
      'derivation':'R226:601/607 residual abstentions are clicked_bbox_only; transfer target color with coarser pre-action representation',
      'selection':{'protocol':'fit p0-p4; validate p5-p9; zero-wrong exact gameplay-frame only','selected':selected,'selected_config':cfg,'candidates':candidates},
      'refit':{'paths':'p0-p9','family':fam,'min_traces':sup,'keys':len(tab),'rejected':dict(rej)},
      'heldout':held,'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False,
                   'next_gate':'if promoted, freeze after R225; otherwise close coarse-local-target family and change representation'},
      'truth':truth()}

def truth():
    return {'public_trace_only':True,'selection_fit_p0_p4_validate_p5_p9_only':True,
      'selected_family_refit_p0_p9_only':True,'training_keys_require_all_occurrences_local_same_target':True,
      'distinct_trace_support_required':True,'r225_precedence_preserved':True,
      'goal_manifold_veto_preserved':True,'heldout_never_updates_models_or_selection':True,
      'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'selected':d['selection']['selected'],'selected_config':d['selection'].get('selected_config'),'refit':d.get('refit'),'heldout':d.get('heldout'),'gate':d.get('zero_wrong_coverage_gain_gate_pass',False)},sort_keys=True))
if __name__=='__main__':main()
