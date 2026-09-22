#!/usr/bin/env python3
"""R247: action-conditional source-free Markov-fidelity gate.

Repairs the R246 collision pattern without using p10-p19 outcomes for selection.
R246 selected one lens per game and produced 171 added exact-frame predictions,
169 correct and 2 wrong. Both frozen wrongs were in sc25 LEFT while the same
game's RESET predictions were correct.

R247 therefore selects a lens independently PER ACTION using p0-p4 fit and
p5-p9 validation. A (game, action) lane is enabled only if validation adds at
least one exact-frame prediction and adds ZERO wrong predictions. p0-p9 then
refits the selected lane; p10-p19 is frozen scoring only.

Exact visible-state/action lookup retains precedence. Game source, upstream
replays, and upstream scores are never read.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG=247

def actions(rows):
    return sorted({r["action"] for r in rows})

def eval_action(rows,exact,tab,lens_name,action):
    sub=[r for r in rows if r["action"]==action]
    return r246.eval_added(sub,exact,tab,lens_name)

def select_per_action(train,val):
    exact=r246.fit_exact(train)
    selected={};diagnostic={}
    all_actions=sorted(set(actions(train))|set(actions(val)))

    # Pure runtime optimization only: each training lens table is identical
    # across actions because action is already part of the abstract key.
    # Precompute it once per lens instead of refitting it once per action.
    lens_tables={name:r246.fit_lens(train,name) for name in r246.LENS_NAMES}
    train_by_action={a:[r for r in train if r["action"]==a] for a in all_actions}

    for action in all_actions:
        cand={}
        for name in r246.LENS_NAMES:
            tab=lens_tables[name]
            met=eval_action(val,exact,tab,name,action)
            cand[name]={
              "keys":len(tab),
              "fidelity":round(r246.markov_fidelity(train_by_action[action],name),6),
              "validation":met,
            }
        zero=[n for n in r246.LENS_NAMES
              if cand[n]["validation"].get("candidate_predictions",0)>0
              and cand[n]["validation"].get("candidate_wrong",0)==0]
        if zero:
            zero.sort(key=lambda n:(-cand[n]["validation"].get("candidate_correct",0),
                                    -cand[n]["fidelity"],
                                    r246.LENS_NAMES.index(n)))
            selected[action]=zero[0]
        diagnostic[action]=cand
    return selected,diagnostic

def evaluate_game(paths):
    ps=sorted(paths,key=r246.pnum)
    nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)):
        raise ValueError(f"{r246.game_id(ps[0])}: exact p0..p19 required, got {nums}")
    tr=r246.transitions(ps[:5]);va=r246.transitions(ps[5:10])
    fit=r246.transitions(ps[:10]);ho=r246.transitions(ps[10:])
    selected,diag=select_per_action(tr,va)
    exact=r246.fit_exact(fit)
    tabs={name:r246.fit_lens(fit,name) for name in set(selected.values())}
    s=Counter(); examples=[]
    by_action=defaultdict(Counter)
    for r in ho:
        s["transitions"]+=1
        if r246.exact_key(r) in exact:
            s["exact_baseline"]+=1;continue
        s["baseline_abstain"]+=1
        action=r["action"]
        name=selected.get(action)
        if name is None:
            s["candidate_abstain"]+=1;continue
        k=r246.stable((r246.lens(name,r["before"]),action))
        pred=tabs[name].get(k)
        if pred is None:
            s["candidate_abstain"]+=1;continue
        s["candidate_predictions"]+=1;by_action[action]["predictions"]+=1
        ok=pred==r["after"]
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        by_action[action]["correct" if ok else "wrong"]+=1
        if len(examples)<30:
            examples.append({"trace":r["trace"],"action":action,"lens":name,"correct":ok})
    p=s["candidate_predictions"];opp=s["baseline_abstain"]
    held={**dict(s),
      "accuracy":round(s["candidate_correct"]/p,6) if p else None,
      "coverage_of_baseline_abstain":round(p/opp,6) if opp else 0.0,
      "by_action":{a:dict(v) for a,v in by_action.items()},
      "examples":examples}
    gain=bool(p>0 and s["candidate_wrong"]==0)
    return {
      "selected_by_action":selected,
      "selection_diagnostic":diag,
      "refit":{"exact_keys":len(exact),"selected_action_count":len(selected)},
      "heldout":held,
      "gain":gain,
    }

def run(paths):
    by=defaultdict(list)
    for p in paths: by[r246.game_id(p)].append(p)
    games={g:evaluate_game(ps) for g,ps in sorted(by.items())}
    agg=Counter();gain_games=[]
    for g,x in games.items():
        h=x["heldout"]
        for k in ("transitions","exact_baseline","baseline_abstain","candidate_predictions","candidate_correct","candidate_wrong"):
            agg[k]+=int(h.get(k,0) or 0)
        if x["gain"]:gain_games.append(g)
    p=agg["candidate_predictions"];opp=agg["baseline_abstain"]
    aggregate={**dict(agg),
      "candidate_accuracy":round(agg["candidate_correct"]/p,6) if p else None,
      "candidate_coverage_of_baseline_abstain":round(p/opp,6) if opp else 0.0,
      "gain_games":gain_games,"gain_game_count":len(gain_games),"game_count":len(games)}
    nondominated=bool(p>0 and agg["candidate_wrong"]==0 and agg["candidate_correct"]>0)
    return {
      "schema":"deus/arc3-r247-action-conditional-markov-gate/1",
      "rung":RUNG,
      "lineage":{"r246":"run35763149532/artifact10712160802",
                 "repair":"per-action validation gate only; no heldout-informed lane selection"},
      "protocol":{"select":"p0-p4 fit / p5-p9 per-action zero-wrong validation",
                  "refit":"p0-p9","frozen_eval":"p10-p19",
                  "exact_baseline_precedence":True},
      "games":games,"aggregate":aggregate,
      "non_dominated_source_side_gain":nondominated,
      "promotion":{"integration_candidate":nondominated,"solver_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"game_source_read":False,
               "selection_uses_p0_p9_only":True,
               "p10_p19_never_updates_selection_or_model":True,
               "r246_wrong_locations_not_encoded_as_rules":True,
               "independent_generalization_claim":False,
               "kaggle_execution":False,"submission_quota_spent":False,
               "owner_score_claim":False}}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"aggregate":d["aggregate"],"gain":d["non_dominated_source_side_gain"],
      "sc25":d["games"].get("sc25-635fd71a",{}).get("heldout"),
      "selected_sc25":d["games"].get("sc25-635fd71a",{}).get("selected_by_action")},sort_keys=True))
if __name__=="__main__": main()
