#!/usr/bin/env python3
"""R272: integrate verified R271 exact-frame UI-mask experts across promoted games.

Selection and expert construction remain p0-p9 only. Frozen p10-p19 scoring:
1) exact visible-state/action baseline
2) per-game UI-mask exact-frame expert only for games in the frozen promoted set
No expert may override an exact baseline prediction.
Union promotion requires zero wrong and positive incremental exact-frame gain.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_ui_mask_exact_frame_271 as r271

RUNG=272
PROMOTED={
"ar25-0c556536","ka59-38d34dbb","lf52-271a04aa","r11l-495a7899",
"re86-8af5384d","s5i5-18d95033","su15-1944f8ab","tn36-ef4dde99",
"tu93-0768757b","vc33-5430563c"}

def rows(paths): return [r for p in paths for r in r251.prepare_rows([p])]

def game_eval(paths):
    ps=sorted(paths,key=r246.pnum)
    gid=r246.game_id(ps[0])
    fit=rows(ps[:10]);ho=rows(ps[10:])
    exact=r271.fit_exact(fit);cand=r271.fit_masked_exact(fit)
    s=Counter()
    for r in ho:
        s["transitions"]+=1
        if r271.exact_key(r) in exact:
            s["baseline_predictions"]+=1;continue
        s["baseline_abstain"]+=1
        if gid not in PROMOTED:
            s["union_abstain"]+=1;continue
        pred=cand.get(r271.masked_key(r))
        if pred is None:
            s["union_abstain"]+=1;continue
        s["union_predictions"]+=1
        if pred==r["after"]: s["union_correct"]+=1
        else: s["union_wrong"]+=1
    p=s["union_predictions"]
    return {**dict(s),"union_accuracy":round(s["union_correct"]/p,6) if p else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input:by[r246.game_id(p)].append(p)
    games={g:game_eval(ps) for g,ps in sorted(by.items())}
    agg=Counter()
    for x in games.values():
        for k in ("transitions","baseline_predictions","baseline_abstain","union_predictions","union_correct","union_wrong","union_abstain"):
            agg[k]+=int(x.get(k,0) or 0)
    p=agg["union_predictions"]
    aggregate={**dict(agg),"game_count":len(games),"promoted_game_count":len(PROMOTED),
      "union_accuracy":round(agg["union_correct"]/p,6) if p else None,
      "union_pass":bool(p>0 and agg["union_wrong"]==0)}
    out={"schema":"deus/arc3-r272-ui-mask-exact-frame-union/1","rung":RUNG,
      "promoted_games":sorted(PROMOTED),"games":games,"aggregate":aggregate,
      "truth":{"public_trace_only":True,"p0_p9_fit_only":True,"p10_p19_frozen":True,
               "exact_baseline_precedence":True,"zero_wrong_required":True,
               "kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(aggregate,sort_keys=True))
if __name__=="__main__":main()
