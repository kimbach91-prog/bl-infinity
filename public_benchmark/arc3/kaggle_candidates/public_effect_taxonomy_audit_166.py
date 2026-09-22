#!/usr/bin/env python3
"""Rung 166: outcome-assisted transition-effect taxonomy audit.

R164 established that the exact pure same-color connected-object translation
family has zero training examples on the pinned public traces. Before building
another predictor, this audit changes representation from *mover identity* to
*effect structure*: diff cardinality, diff connected components, border contact,
old->new color-pair concentration, and compactness of the changed-region bbox.

This rung is explicitly outcome-assisted structural research only. It makes no
pre-outcome prediction and therefore cannot claim generalization, solver gain,
or Kaggle gain. Its purpose is to select the next executable representation
instead of blind-retrying an inapplicable mover family.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path
from typing import Any
import public_executable_world_model_134 as base

RUNG=166
Grid=list[list[int]]


def components(cells:set[tuple[int,int]])->list[list[tuple[int,int]]]:
    out=[]
    unseen=set(cells)
    while unseen:
        seed=unseen.pop(); stack=[seed]; comp=[seed]
        while stack:
            r,c=stack.pop()
            for q in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if q in unseen:
                    unseen.remove(q); stack.append(q); comp.append(q)
        out.append(comp)
    return out


def classify(before:Grid,after:Grid)->dict[str,Any]:
    h=len(before);w=len(before[0])
    edits=[]
    for r in range(h):
        for c in range(w):
            if before[r][c]!=after[r][c]:
                edits.append((r,c,before[r][c],after[r][c]))
    n=len(edits)
    if n==0:
        return {'class':'identity','changed':0,'components':0,'border':False,'single_pair':True,'bbox_area':0,'compactness':None}
    coords={(r,c) for r,c,_,_ in edits}
    comps=components(coords)
    r0=min(r for r,_,_,_ in edits);r1=max(r for r,_,_,_ in edits)
    c0=min(c for _,c,_,_ in edits);c1=max(c for _,c,_,_ in edits)
    area=(r1-r0+1)*(c1-c0+1)
    pairs=Counter((old,new) for _,_,old,new in edits)
    border=any(r in (0,h-1) or c in (0,w-1) for r,c,_,_ in edits)
    if n==1: cls='single_cell'
    elif n<=4: cls='sparse_2_4'
    elif n<=16: cls='sparse_5_16'
    elif n<=64: cls='medium_17_64'
    else: cls='dense_65_plus'
    return {
        'class':cls,'changed':n,'components':len(comps),'largest_component':max(map(len,comps)),
        'border':border,'single_pair':len(pairs)==1,'pair_count':len(pairs),
        'dominant_pair_fraction':round(max(pairs.values())/n,6),'bbox_area':area,
        'compactness':round(n/area,6),'pairs':pairs,
    }


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    classes=Counter(); changed_counts=Counter(); component_counts=Counter(); pair_counter=Counter()
    border=single_pair=compact=total=0
    per_action:dict[str,Counter]= {}
    pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        before=base.as_grid(pre['board']);after=base.as_grid(e['board']);action=base.action_name(e);pre=e
        if not base.same_shape(before,after):continue
        d=classify(before,after); total+=1
        classes[d['class']]+=1; changed_counts[d['changed']]+=1; component_counts[d['components']]+=1
        border += int(d['border']); single_pair += int(d['single_pair'])
        compact += int(d['changed']>0 and d['compactness']>=0.75)
        if action not in per_action:per_action[action]=Counter()
        per_action[action][d['class']]+=1
        if d['changed']:
            pair_counter.update(d['pairs'])
    return {
        'transitions':total,'classes':dict(classes),'per_action':{a:dict(c) for a,c in sorted(per_action.items())},
        'border_touching':border,'single_color_pair_effects':single_pair,'high_compactness_effects':compact,
        'changed_count_top20':changed_counts.most_common(20),'component_count_top10':component_counts.most_common(10),
        'color_pair_top20':[((int(a),int(b)),n) for (a,b),n in pair_counter.most_common(20)],
    }


def run(paths:list[Path])->dict[str,Any]:
    parts=[]
    for p in paths:parts.append(audit_trace(base.load_events(p)))
    total=sum(x['transitions'] for x in parts)
    classes=Counter(); action_classes:dict[str,Counter]={}; pairs=Counter()
    for x in parts:
        classes.update(x['classes'])
        for a,c in x['per_action'].items():action_classes.setdefault(a,Counter()).update(c)
        for (pair,n) in x['color_pair_top20']:pairs[tuple(pair)]+=n
    non_identity=total-classes.get('identity',0)
    sparse=classes.get('single_cell',0)+classes.get('sparse_2_4',0)+classes.get('sparse_5_16',0)
    recommendation='SPARSE_EFFECT_DECOMPOSITION' if non_identity and sparse/non_identity>=0.5 else 'DENSE_OR_RENDERER_STATE_DYNAMICS'
    return {
        'schema':'deus/arc3-public-effect-taxonomy-audit/1','rung':RUNG,
        'execution_class':'CPU_PUBLIC_TRACE_OUTCOME_ASSISTED_EFFECT_STRUCTURE_AUDIT',
        'representation_change_from_rung164':{'changed':True,'change':'replace inapplicable pure-object-translation hypothesis with outcome-assisted taxonomy of changed-region structure to choose the next executable dynamics representation'},
        'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
        'traces':[{'path':str(p),'audit':a} for p,a in zip(paths,parts)],
        'aggregate':{'transitions':total,'classes':dict(classes),'non_identity':non_identity,'sparse_up_to_16':sparse,'sparse_fraction_of_non_identity':round(sparse/non_identity,6) if non_identity else None,'per_action':{a:dict(c) for a,c in sorted(action_classes.items())},'recommendation':recommendation},
        'diagnostic_gate':'EFFECT_TAXONOMY_COMPLETE',
        'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
        'truth':{'public_trace_only':True,'outcome_assisted_analysis':True,'preoutcome_prediction_made':False,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
