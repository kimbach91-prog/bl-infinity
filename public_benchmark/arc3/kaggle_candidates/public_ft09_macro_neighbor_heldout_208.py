#!/usr/bin/env python3
"""R208: frozen p10-p19 gate for the R207 ft09 macro-neighbor selector.

R207 found a high-cardinality pre-action selector on p0-p9:
  (current tile color, ordered N/E/S/W macro-neighbors, global core-tile counts)
with 99.1813% deterministic training examples. R208 tests the smallest falsifier:
fit that exact selector on p0-p9 only, freeze it, then evaluate target-color
predictions on p10-p19 without model updates. This is iterative public-heldout
mechanism research, not independent generalization and not full-frame solving.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
import public_ft09_macro_neighbor_rule_207 as r207

RUNG=208
GAME='ft09-0d8bbf25'


def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1


def transitions(path:Path):
    ev=base.load_events(path); pre=ev[0]; step=0
    for e in ev[1:]:
        if e.get('type')!='action':
            pre=e; continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board'])
        a=base.action_name(e); pre=e; step+=1
        if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':
            continue
        click=c191.parse_mouse(a)
        if click is None: continue
        rr,cc=click; h,w=len(before),len(before[0]); rr=max(0,min(h-1,rr)); cc=max(0,min(w-1,cc))
        bb=r207.comp_bbox(before,rr,cc)
        if bb[4]!=36 or (bb[2]-bb[0]+1,bb[3]-bb[1]+1)!=(6,6):
            continue
        ctx=r207.macro_context(before,bb); cur=ctx['current']
        key=repr((cur,ctx['four'],ctx['global_core_counts_bucket']))
        target=r207.dominant_target(before,after,bb)
        yield {'trace':path.name,'step':step,'key':key,'current':cur,'target':target,
               'four':ctx['four'],'global':ctx['global_core_counts_bucket']}


def run(paths):
    ps=sorted(paths,key=pnum); nums=[pnum(x) for x in ps]
    if nums!=list(range(20)):
        raise ValueError(f'exact p0..p19 required; got {nums}')
    train=ps[:10]; held=ps[10:]

    obs=defaultdict(Counter); train_stats=Counter()
    for path in train:
        for x in transitions(path):
            train_stats['eligible_6x6_mouse']+=1
            if x['target']==x['current']:
                train_stats['identity']+=1
                continue
            train_stats['changed']+=1
            obs[x['key']][x['target']]+=1

    table={k:next(iter(c)) for k,c in obs.items() if len(c)==1}
    conflicted={k:dict(c) for k,c in obs.items() if len(c)>1}
    deterministic_examples=sum(sum(obs[k].values()) for k in table)
    changed_examples=sum(sum(c.values()) for c in obs.values())

    agg=Counter(); by_trace={}; mistakes=[]; correct_examples=[]
    for path in held:
        s=Counter()
        for x in transitions(path):
            s['eligible_6x6_mouse']+=1; agg['eligible_6x6_mouse']+=1
            changed=(x['target']!=x['current'])
            if changed:
                s['actual_changed']+=1; agg['actual_changed']+=1
            else:
                s['actual_identity']+=1; agg['actual_identity']+=1
            pred=table.get(x['key'])
            if pred is None:
                s['abstain']+=1; agg['abstain']+=1
                continue
            s['predictions']+=1; agg['predictions']+=1
            if changed:
                s['predicted_on_changed']+=1; agg['predicted_on_changed']+=1
            else:
                s['predicted_on_identity']+=1; agg['predicted_on_identity']+=1
            if pred==x['target']:
                s['correct']+=1; agg['correct']+=1
                if changed:
                    s['correct_changed']+=1; agg['correct_changed']+=1
                if len(correct_examples)<20:
                    correct_examples.append({**x,'pred':pred})
            else:
                s['wrong']+=1; agg['wrong']+=1
                if len(mistakes)<30:
                    mistakes.append({**x,'pred':pred})
        p=s['predictions']; eligible=s['eligible_6x6_mouse']; ach=s['actual_changed']
        by_trace[path.name]={**dict(s),
            'accuracy':round(s['correct']/p,6) if p else None,
            'coverage':round(p/eligible,6) if eligible else 0.0,
            'changed_recall':round(s['correct_changed']/ach,6) if ach else None}

    p=agg['predictions']; eligible=agg['eligible_6x6_mouse']; ach=agg['actual_changed']
    accuracy=agg['correct']/p if p else 0.0
    coverage=p/eligible if eligible else 0.0
    changed_recall=agg['correct_changed']/ach if ach else 0.0
    mechanism_gate=bool(p>=100 and accuracy>=0.99 and coverage>=0.10 and changed_recall>=0.10)

    return {
      'schema':'deus/arc3-ft09-macro-neighbor-heldout/1','rung':RUNG,'game':GAME,
      'protocol':{
        'fit':'p0-p9 changed 6x6 MOUSE tile effects only',
        'selector':'current_four_global exact symbolic key from R207',
        'freeze':'p10-p19 never update model',
        'gate':'predictions>=100 AND target_accuracy>=0.99 AND coverage>=0.10 AND changed_recall>=0.10'},
      'train':{
        **dict(train_stats),'selector_values':len(obs),'deterministic_values':len(table),
        'conflicted_values':len(conflicted),'changed_examples':changed_examples,
        'deterministic_examples':deterministic_examples,
        'deterministic_fraction':round(deterministic_examples/changed_examples,6) if changed_examples else 0.0},
      'heldout':{
        'all':{**dict(agg),'accuracy':round(accuracy,6),'coverage':round(coverage,6),'changed_recall':round(changed_recall,6)},
        'by_trace':by_trace},
      'mechanism_gate_pass':mechanism_gate,
      'promotion':{
        'mechanism_gate':mechanism_gate,
        'solver_promotion':False,
        'kaggle_packaging':False,
        'reason':'mechanism-only target-color gate; full-frame HUD/timer/reset/goal effects remain unresolved'},
      'mistakes':mistakes,'correct_examples':correct_examples,
      'truth':{
        'public_trace_only':True,'iterative_public_heldout_research':True,
        'independent_generalization_claim':False,'heldout_never_updates_model':True,
        'pre_action_selector_only':True,'outcome_used_for_evaluation_only_on_heldout':True,
        'full_frame_solver_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False}}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); d=run(a.input); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'train':d['train'],'heldout':d['heldout']['all'],'mechanism_gate_pass':d['mechanism_gate_pass'],'promotion':d['promotion']},sort_keys=True))

if __name__=='__main__': main()
