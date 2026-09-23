#!/usr/bin/env python3
"""R272: union/integration audit for zero-wrong R271 exact-frame experts.

Only the 10 per-game experts that already passed frozen p10-p19 zero-wrong
incremental gates are admitted. The union keeps exact visible-state/action
baseline precedence, then applies the corresponding per-game UI-mask exact-frame
expert. No threshold retuning, no cross-game voting, no Kaggle execution.

The purpose is to verify that the admitted experts remain conflict-free and
non-dominated when evaluated as one public stack.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_ui_mask_markov_diag_268 as r268
import public_ui_mask_exact_frame_271 as r271

PROMOTED=set("ar25-0c556536 ka59-38d34dbb lf52-271a04aa r11l-495a7899 re86-8af5384d s5i5-18d95033 su15-1944f8ab tn36-ef4dde99 tu93-0768757b vc33-5430563c".split())

def rows(paths):
    return [r for p in paths for r in r251.prepare_rows([p])]

def eval_game(game,paths):
    ps=sorted(paths,key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(20)):
        raise ValueError(f"{game}: exact p0..p19 required")
    fit=rows(ps[:10]);ho=rows(ps[10:])
    exact=r271.fit_exact(fit)
    cand=r271.fit_masked_exact(fit) if game in PROMOTED else {}
    s=Counter()
    for r in ho:
        s["transitions"]+=1
        if r271.exact_key(r) in exact:
            s["baseline_predictions"]+=1
            continue
        s["baseline_abstain"]+=1
        if game not in PROMOTED:
            s["union_abstain"]+=1
            continue
        pred=cand.get(r271.masked_key(r))
        if pred is None:
            s["union_abstain"]+=1
            continue
        s["union_predictions"]+=1
        s["union_correct" if pred==r["after"] else "union_wrong"]+=1
    return dict(s)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input:by[r246.game_id(p)].append(p)
    games={g:eval_game(g,ps) for g,ps in sorted(by.items())}
    agg=Counter()
    for g,x in games.items():
        for k,v in x.items():agg[k]+=int(v)
    aggregate={**dict(agg),"game_count":len(games),"promoted_game_count":len(PROMOTED),
               "promoted_games":sorted(PROMOTED)}
    aggregate["union_accuracy"]=round(agg["union_correct"]/agg["union_predictions"],6) if agg["union_predictions"] else None
    aggregate["non_dominated"]=bool(agg["union_predictions"]>0 and agg["union_wrong"]==0 and agg["union_correct"]>0)
    out={"schema":"deus/arc3-r272-public25-exact-frame-union/1","aggregate":aggregate,"games":games,
         "truth":{"public_trace_only":True,"game_source_read":False,"expert_set_frozen_from_r271":True,
                  "exact_baseline_precedence":True,"retune":False,"kaggle_execution":False,
                  "competition_submission":False,"submission_quota_spent":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(aggregate,sort_keys=True))
if __name__=="__main__":main()
