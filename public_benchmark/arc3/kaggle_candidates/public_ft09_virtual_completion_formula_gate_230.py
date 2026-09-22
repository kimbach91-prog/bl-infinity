#!/usr/bin/env python3
"""R230: generic virtual-post structural completion formula gate.

R228 exact-ish pre-action completion fingerprints did not transfer. R229 then
showed the three completion false positives share an identical virtual-post
low-dimensional state, while no single scalar feature alone is pure among the
R227 candidate population.  R230 therefore changes representation to generic
relations on the *proposed* post-click board rather than absolute pre-action
fingerprints.

Protocol:
- reuse frozen R227 target family (current_ring2hist|t2);
- fit a target table on p0-p4 only for completion-formula training/validation;
- from every eligible p0-p4 row for which that target table proposes a target,
  construct the virtual local recolor and fit completion-only relation keys;
- validate on p5-p9 with the same p0-p4 target table, requiring zero completion
  false positives;
- select without p10-p19, refit target table + completion keys on p0-p9;
- apply only as an ABSTAIN veto ahead of frozen R227 heldout candidates.

PUBLIC_OFFLINE only.  This is not hidden Kaggle score or independent generalization.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_low_confidence_goal_manifold_veto_225 as r225
import public_ft09_coarse_local_target_gate_227 as r227
import public_ft09_completion_invariant_diag_229 as r229

RUNG=230; GAME='ft09-0d8bbf25'
FAMILIES=('macro_rel_level','macro_shape_level','macro_neighborhood_level','component_macro_level','macro_rel_nolevel','macro_neighborhood_nolevel')
SUPPORTS=(2,3)

def pnum(p):
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def sig(fam,f):
    balanced=(f['macro6_distinct']==2 and 2*f['macro6_max_count']==f['macro6_total'])
    target_half=(2*f['macro6_target_count']==f['macro6_total'])
    target_is_max=(f['macro6_target_count']==f['macro6_max_count'])
    base=(f['macro6_total'],f['macro6_distinct'],f['macro6_count_shape'],balanced,target_half,target_is_max)
    if fam=='macro_rel_level': return (f['level'],)+base
    if fam=='macro_shape_level': return (f['level'],f['macro6_total'],f['macro6_distinct'],f['macro6_count_shape'],f['macro6_target_count'],f['macro6_max_count'])
    if fam=='macro_neighborhood_level': return (f['level'],)+base+(f['same_nbr4'],f['same_nbr8'],f['nbr4_count_shape'],f['nbr8_count_shape'])
    if fam=='component_macro_level': return (f['level'],f['macro6_total'],f['macro6_distinct'],f['macro6_count_shape'],f['total_components'],f['target_component_size'],f['target_component_hw'])
    if fam=='macro_rel_nolevel': return base
    if fam=='macro_neighborhood_nolevel': return base+(f['same_nbr4'],f['same_nbr8'],f['nbr4_count_shape'],f['nbr8_count_shape'])
    raise KeyError(fam)

def target_table(paths):
    # R227 selected family is already frozen by its prior p0-p4/p5-p9 protocol.
    return r227.fit(paths,'current_ring2hist',2)[0]

def examples(paths,tab):
    out=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            lm=meta.get(r['step0']);tgt=tab.get(repr(r227.feat('current_ring2hist',r,lm)))
            if tgt is None:continue
            f=r229.feature(r,lm,tgt);completion=bool(lm and lm['level_after']>lm['level_before'])
            out.append({'p':r['p'],'step0':r['step0'],'path':r['path'],'completion':completion,'f':f})
    return out

def fit_model(xs,fam,support):
    g=defaultdict(lambda:{'lab':Counter(),'tr':defaultdict(set)})
    for x in xs:
        k=repr(sig(fam,x['f']));z=g[k];z['lab'][x['completion']]+=1;z['tr'][x['completion']].add(x['path'])
    m=set();rej=Counter()
    for k,z in g.items():
        if z['lab'][False]:rej['noncompletion_collision']+=1;continue
        if not z['lab'][True]:rej['no_completion']+=1;continue
        if len(z['tr'][True])<support:rej['low_trace_support']+=1;continue
        m.add(k)
    return m,dict(rej)

def evaluate(xs,m,fam):
    s=Counter();ex=[]
    for x in xs:
        pred=repr(sig(fam,x['f'])) in m;actual=x['completion'];s['examples']+=1
        if actual:s['actual_completion']+=1
        else:s['actual_noncompletion']+=1
        if pred:
            s['veto']+=1;s['tp' if actual else 'fp']+=1
            if len(ex)<20:ex.append({'p':x['p'],'step0':x['step0'],'completion':actual})
        elif actual:s['fn']+=1
    return {**dict(s),'examples_list':ex}

def choose(train,val):
    c={}
    for fam in FAMILIES:
      for sup in SUPPORTS:
        m,rej=fit_model(train,fam,sup);v=evaluate(val,m,fam)
        c[f'{fam}|t{sup}']={'family':fam,'support':sup,'keys':len(m),'rejected':rej,'validation':v}
    safe=[(k,v) for k,v in c.items() if v['validation'].get('veto',0)>0 and v['validation'].get('fp',0)==0]
    if not safe:return None,c
    safe.sort(key=lambda kv:(-kv[1]['validation'].get('tp',0),-kv[1]['support'],FAMILIES.index(kv[1]['family'])))
    return safe[0][0],c

def heldout(paths,train10,fam,support,model,tab10):
    m=r221.build_models(train10);s=Counter();wrong=[];veto=[]
    for p in paths:
      meta=r217.level_meta(p)
      for r in r212.all_rows(p):
        if not r['eligible']:continue
        s['eligible']+=1;lm=meta.get(r['step0'])
        pred,_=r221.r218_predict(r,lm,m)
        if pred is None:pred,_=r221.r219_predict(r,lm,m)
        if pred is None:pred,_,_=r225.lowbase_goal_veto(r,lm,m)
        if pred is not None:s['incumbent']+=1;continue
        tgt=tab10.get(repr(r227.feat('current_ring2hist',r,lm)))
        if tgt is None or r227.goal_veto(r,lm,tgt,m) is not None:s['abstain']+=1;continue
        f=r229.feature(r,lm,tgt)
        if repr(sig(fam,f)) in model:
            s['completion_veto']+=1;s['abstain']+=1
            actual=bool(lm and lm['level_after']>lm['level_before'])
            s['veto_tp' if actual else 'veto_fp']+=1
            if len(veto)<20:veto.append({'p':r['p'],'step0':r['step0'],'action':r['action'],'actual_completion':actual,'signature':repr(sig(fam,f))})
            continue
        local=r229.gp(r212.recolor_bbox(r['before'],r['bbox'],tgt));ok=local==r229.gp(r['after'])
        s['candidate']+=1;s['correct' if ok else 'wrong']+=1
        if not ok and len(wrong)<20:wrong.append({'p':r['p'],'step0':r['step0'],'action':r['action'],'completion':bool(lm and lm['level_after']>lm['level_before']),'signature':repr(sig(fam,f))})
    return {**dict(s),'accuracy':round(s['correct']/s['candidate'],6) if s['candidate'] else None,'veto_examples':veto,'wrong_examples':wrong}

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('p0..p19 required')
    tab05=target_table(ps[:5]);tr=examples(ps[:5],tab05);va=examples(ps[5:10],tab05)
    selected,cand=choose(tr,va)
    if selected is None:return {'schema':'deus/arc3-ft09-virtual-completion-formula/1','rung':RUNG,'selection':{'selected':None,'candidates':cand},'heldout':None,'gate':False,'truth':truth()}
    cfg=cand[selected];tab10=target_table(ps[:10]);all10=examples(ps[:10],tab10);model,rej=fit_model(all10,cfg['family'],cfg['support'])
    h=heldout(ps[10:],ps[:10],cfg['family'],cfg['support'],model,tab10)
    # Strict public coverage-expert gate: no wrong surviving and at least one exact candidate beyond incumbent.
    gate=bool(h.get('candidate',0)>0 and h.get('wrong',0)==0 and h.get('correct',0)>0 and h.get('veto_fp',0)==0)
    return {'schema':'deus/arc3-ft09-virtual-completion-formula/1','rung':RUNG,'selection':{'protocol':'target+formula fit p0-p4; validate p5-p9 zero-FP; refit p0-p9','selected':selected,'selected_config':cfg,'candidates':cand},'refit':{'keys':len(model),'rejected':rej},'heldout':h,'gate':gate,'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False},'truth':truth()}

def truth():return {'public_trace_only':True,'formula_selection_excludes_p10_p19':True,'heldout_never_updates_model_or_selection':True,'virtual_state_uses_frozen_r227_target_proposal':True,'veto_can_only_abstain':True,'r225_precedence_preserved':True,'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'selection':d['selection'].get('selected'),'config':d['selection'].get('selected_config'),'refit':d.get('refit'),'heldout':d.get('heldout'),'gate':d['gate']},sort_keys=True))
if __name__=='__main__':main()
