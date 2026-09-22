#!/usr/bin/env python3
"""R226: outcome-assisted diagnostic for the R225 residual abstain set.

Purpose: explain the remaining frozen p10-p19 PUBLIC_OFFLINE abstentions after
R225 without promoting heldout labels into a predictor.  R225 itself remains
frozen.  This diagnostic rebuilds only the p0-p9 R225 models, replays the exact
R225 precedence, then uses heldout outcomes solely to classify residual
mechanisms (identity/local-only/scene-or-global/completion) and missing-evidence
classes (unseen base, support-1, goal-manifold veto).

No threshold/feature/policy is selected from heldout data and no prediction is
added here.  Any next candidate must be derived separately and frozen before a
new heldout evaluation.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_low_confidence_goal_manifold_veto_225 as r225

RUNG=226
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def diff_stats(before,after,bb):
    # gameplay rows only; HUD row is excluded
    b=gp(before); a=gp(after)
    r0,c0,r1,c1,_=bb
    total=inside=outside=0
    for rr,(rb,ra) in enumerate(zip(b,a)):
        for cc,(x,y) in enumerate(zip(rb,ra)):
            if x==y: continue
            total+=1
            if r0<=rr<=r1 and c0<=cc<=c1: inside+=1
            else: outside+=1
    return {'total':total,'inside':inside,'outside':outside}

def evidence_class(r,m):
    ent=m['base'].get(repr(r['base']))
    if ent is None:
        return 'base_unseen_or_nondeterministic',None
    sup=int(ent.get('support',0))
    if sup<2: return 'base_support1',sup
    if sup>=5: return 'base_ge5_unexpected_after_r219',sup
    return 'base_support2to4',sup

def actual_mechanism(r,lm):
    ds=diff_stats(r['before'],r['after'],r['bbox'])
    completion=bool(lm is not None and lm['level_after']>lm['level_before'])
    if ds['total']==0: cls='identity'
    elif ds['outside']==0: cls='clicked_bbox_only'
    elif completion: cls='level_completion_scene'
    elif ds['outside']<=8: cls='sparse_outside_bbox'
    else: cls='scene_or_global'
    return cls,completion,ds

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')
    train=ps[:10]; held=ps[10:]
    m=r221.build_models(train)

    s=Counter(); evidence=Counter(); mechanisms=Counter(); cross=defaultdict(Counter)
    action_mech=defaultdict(Counter); level_mech=defaultdict(Counter)
    support_mech=defaultdict(Counter); examples=[]; vetoes=Counter()

    for p in held:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1; lm=meta.get(r['step0'])

            pred,_=r221.r218_predict(r,lm,m)
            if pred is None: pred,_=r221.r219_predict(r,lm,m)
            if pred is not None:
                s['covered_before_r225']+=1
                continue

            pred,_,veto=r225.lowbase_goal_veto(r,lm,m)
            if pred is not None:
                s['r225_added']+=1
                continue

            # exact residual abstain population only
            s['residual_abstain']+=1
            evc,sup=evidence_class(r,m)
            evidence[evc]+=1
            if veto is not None:
                evc='goal_manifold_veto'
                evidence[evc]+=1; vetoes[veto]+=1

            mech,completion,ds=actual_mechanism(r,lm)
            mechanisms[mech]+=1
            cross[evc][mech]+=1
            action_mech[r['action'].split('(')[0]][mech]+=1
            level_mech[str(lm['level_before'] if lm else None)][mech]+=1
            support_mech[str(sup if sup is not None else 'none')][mech]+=1

            if len(examples)<80:
                examples.append({
                    'trace':r['path'],'p':r['p'],'step0':r['step0'],
                    'action':r['action'],'prev_action':r['prev_action'],'run_len':r['run_len'],
                    'level_before':lm['level_before'] if lm else None,
                    'level_after':lm['level_after'] if lm else None,
                    'score_before':lm['score_before'] if lm else None,
                    'evidence_class':evc,'base_support':sup,'veto':veto,
                    'actual_mechanism':mech,'completion':completion,'diff':ds,
                })

    assert s['eligible']==914,dict(s)
    assert s['covered_before_r225']==296,dict(s)
    assert s['r225_added']==11,dict(s)
    assert s['residual_abstain']==607,dict(s)

    # Diagnostics only: rank mechanism/evidence buckets by population.  This is
    # not a predictor-selection rule and is intentionally forbidden promotion.
    ranked_mechanisms=sorted(mechanisms.items(),key=lambda kv:(-kv[1],kv[0]))
    ranked_evidence=sorted(evidence.items(),key=lambda kv:(-kv[1],kv[0]))
    return {
      'schema':'deus/arc3-ft09-r225-residual-temporal-structural-diagnostic/1',
      'rung':RUNG,'game':GAME,
      'population':dict(s),
      'residual':{
        'evidence_classes':dict(evidence),
        'actual_mechanisms':dict(mechanisms),
        'ranked_evidence':ranked_evidence,
        'ranked_mechanisms':ranked_mechanisms,
        'evidence_x_mechanism':{k:dict(v) for k,v in cross.items()},
        'action_x_mechanism':{k:dict(v) for k,v in action_mech.items()},
        'level_x_mechanism':{k:dict(v) for k,v in level_mech.items()},
        'support_x_mechanism':{k:dict(v) for k,v in support_mech.items()},
        'veto_counts':dict(vetoes),'examples':examples,
      },
      'promotion':{
        'diagnostic_only':True,'coverage_expert_promotion':False,
        'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'derive one p0-p9-grounded mechanism for the dominant residual class, freeze it, then run a new heldout gate',
      },
      'truth':{
        'public_trace_only':True,'r225_models_fit_p0_p9_only':True,
        'r225_precedence_replayed_unchanged':True,
        'heldout_outcomes_used_for_diagnostic_taxonomy':True,
        'heldout_outcomes_used_for_predictor_selection':False,
        'heldout_updates_models':False,'independent_generalization_claim':False,
        'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'population':d['population'],'ranked_evidence':d['residual']['ranked_evidence'],'ranked_mechanisms':d['residual']['ranked_mechanisms'],'veto':d['residual']['veto_counts'],'promotion':d['promotion']},sort_keys=True))
if __name__=='__main__':main()
