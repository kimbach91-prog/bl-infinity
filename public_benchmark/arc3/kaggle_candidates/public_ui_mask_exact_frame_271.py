#!/usr/bin/env python3
"""R271: exact-frame incremental gate for UI-masked public ARC-AGI-3 states.

Selection uses only p0-p9:
- p0-p4 / p5-p9 reproduce the R268 game-level UI-mask signal.
- p0-p9 refit exact baseline and masked-state/action -> exact-next-frame table.

Frozen p10-p19:
- exact visible-state/action baseline has precedence.
- candidate acts only when exact baseline abstains.
- candidate table must be deterministic to ONE exact next frame and have support
  from >=2 distinct exact pre-states in p0-p9.
- promotion requires >=1 incremental exact-frame prediction and ZERO wrong.

This is reused public-development evidence, not hidden/Kaggle evidence.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_ui_mask_markov_diag_268 as r268

RUNG=271
MIN_PRESTATE_SUPPORT=2

def rows(paths):
    return [r for p in paths for r in r251.prepare_rows([p])]

def exact_key(r):
    return r246.digest({"before":r["before"],"action":r["action"]})

def fit_exact(rs):
    obs=defaultdict(Counter); frame={}
    for r in rs:
        k=exact_key(r); d=r246.digest(r["after"])
        obs[k][d]+=1; frame[(k,d)]=r["after"]
    out={}
    for k,c in obs.items():
        if len(c)==1:
            d=next(iter(c)); out[k]=frame[(k,d)]
    return out

def masked_key(r):
    return (r246.digest(r268.masked(r["before"])),r["action"])

def fit_masked_exact(rs):
    obs=defaultdict(Counter); prestates=defaultdict(set); frame={}
    for r in rs:
        k=masked_key(r); d=r246.digest(r["after"])
        obs[k][d]+=1
        prestates[k].add(r246.digest(r["before"]))
        frame[(k,d)]=r["after"]
    out={}
    for k,c in obs.items():
        if len(c)!=1 or len(prestates[k])<MIN_PRESTATE_SUPPORT:
            continue
        d=next(iter(c)); out[k]=frame[(k,d)]
    return out

def selected_p0_p9(ps):
    tr=rows(ps[:5]); va=rows(ps[5:10])
    raw,_=r268.fit_table(tr,"raw"); mask,_=r268.fit_table(tr,"ui_mask")
    rv=r268.evaluate(va,raw,"raw"); mv=r268.evaluate(va,mask,"ui_mask")
    selected=bool(int(mv.get("correct",0))>int(rv.get("correct",0)) and int(mv.get("wrong",0))<=int(rv.get("wrong",0)))
    return selected,{"raw":rv,"ui_mask":mv}

def eval_game(paths):
    ps=sorted(paths,key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(20)):
        raise ValueError("exact p0..p19 required")
    selected,selection=selected_p0_p9(ps)
    fit=rows(ps[:10]); ho=rows(ps[10:])
    exact=fit_exact(fit); cand=fit_masked_exact(fit)
    s=Counter(); examples=[]
    for r in ho:
        s["transitions"]+=1
        if exact_key(r) in exact:
            s["baseline_predictions"]+=1
            continue
        s["baseline_abstain"]+=1
        if not selected:
            s["candidate_abstain"]+=1; continue
        pred=cand.get(masked_key(r))
        if pred is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        ok=pred==r["after"]
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        if len(examples)<20:
            examples.append({"trace":r.get("trace"),"action":r["action"],"correct":ok})
    p=s["candidate_predictions"]; opp=s["baseline_abstain"]
    held={**dict(s),
      "candidate_accuracy":round(s["candidate_correct"]/p,6) if p else None,
      "incremental_coverage":round(p/opp,6) if opp else 0.0,
      "examples":examples}
    promote=bool(selected and p>0 and s["candidate_wrong"]==0)
    return {
      "selected_p0_p9":selected,"selection":selection,
      "fit":{"exact_keys":len(exact),"masked_exact_keys":len(cand),"min_prestates":MIN_PRESTATE_SUPPORT},
      "heldout":held,"exact_frame_promoted":promote
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input:by[r246.game_id(p)].append(p)
    games={g:eval_game(ps) for g,ps in sorted(by.items())}
    promoted=[g for g,x in games.items() if x["exact_frame_promoted"]]
    agg=Counter()
    for x in games.values():
        h=x["heldout"]
        for k in ("transitions","baseline_predictions","baseline_abstain","candidate_predictions","candidate_correct","candidate_wrong"):
            agg[k]+=int(h.get(k,0) or 0)
    p=agg["candidate_predictions"]
    aggregate={**dict(agg),"game_count":len(games),"promoted_games":promoted,"promoted_count":len(promoted),
      "candidate_accuracy":round(agg["candidate_correct"]/p,6) if p else None}
    out={"schema":"deus/arc3-r271-ui-mask-exact-frame-incremental/1","rung":RUNG,
      "protocol":{"selection":"p0-p4 fit / p5-p9 signal","refit":"p0-p9","frozen_eval":"p10-p19",
                  "exact_baseline_precedence":True,"min_distinct_prestates":MIN_PRESTATE_SUPPORT},
      "games":games,"aggregate":aggregate,
      "truth":{"public_trace_only":True,"game_source_read":False,"selection_uses_p0_p9_only":True,
               "p10_p19_never_updates_model_or_selection":True,"exact_frame_scoring":True,
               "independent_generalization_claim":False,"kaggle_execution":False,
               "competition_submission":False,"submission_quota_spent":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(aggregate,sort_keys=True))
if __name__=="__main__":main()
