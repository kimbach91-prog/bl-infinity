#!/usr/bin/env python3
"""R308: frozen p5-p9 replay for the four R307 meter signals.

R307 p0-p4 five-fold LOTO nominated meter as a zero-wrong exact-frame
incremental representation for:
  bp35-0a0ad940, sb26-7fbdac44, ls20-9607627b, sp80-589a99af

R308 freezes those game/mode identities before staging p5-p9. It fits p0-p4
only, gives exact visible-state/action baseline precedence, then replays p5-p9.
p10-p19 are forbidden. This is source-assisted public-development stability
evidence, not independent hidden/Kaggle evidence.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251

RUNG=308
GAMES={
 "bp35-0a0ad940","sb26-7fbdac44","ls20-9607627b","sp80-589a99af"
}
MIN_PRESTATES=2
MIN_TRACES=2
MODE="meter"


def exact_key(r): return r246.digest({"b":r["before"],"a":r["action"]})
def abs_key(r): return r246.stable((r["before_features"][MODE],r["action"]))


def fit_exact(rows):
    obs=defaultdict(Counter); frame={}
    for r in rows:
        k=exact_key(r); d=r["after_digest"]; obs[k][d]+=1; frame[(k,d)]=r["after"]
    return {k:frame[(k,next(iter(c)))] for k,c in obs.items() if len(c)==1}


def fit_meter(rows):
    obs=defaultdict(Counter); prestates=defaultdict(set); traces=defaultdict(set); frame={}
    for r in rows:
        k=abs_key(r); d=r["after_digest"]
        obs[k][d]+=1; prestates[k].add(r["before_digest"]); traces[k].add(r["trace"]); frame[(k,d)]=r["after"]
    tab={}
    for k,c in obs.items():
        if len(c)!=1 or len(prestates[k])<MIN_PRESTATES or len(traces[k])<MIN_TRACES: continue
        d=next(iter(c)); tab[k]=frame[(k,d)]
    return tab,{"observed_keys":len(obs),"safe_keys":len(tab)}


def evaluate(rows,exact,tab):
    s=Counter()
    for r in rows:
        s["transitions"]+=1
        if exact_key(r) in exact:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        pred=tab.get(abs_key(r))
        if pred is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        s["candidate_correct" if pred==r["after"] else "candidate_wrong"]+=1
    p=s["candidate_predictions"]
    s["accuracy"]=round(s["candidate_correct"]/p,6) if p else None
    return dict(s)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!=GAMES: raise SystemExit(f"exact frozen games required; got {sorted(by)}")

    games={}; pass_games=[]
    for g in sorted(GAMES):
        ps=sorted(by[g],key=r246.pnum)
        if [r246.pnum(p) for p in ps]!=list(range(10)): raise SystemExit(f"{g}: exact p0-p9 required")
        train=[r for p in ps[:5] for r in r251.prepare_rows([p])]
        replay=[r for p in ps[5:] for r in r251.prepare_rows([p])]
        exact=fit_exact(train); tab,fit=fit_meter(train); val=evaluate(replay,exact,tab)
        gate=bool(val.get("candidate_predictions",0)>0 and val.get("candidate_wrong",0)==0 and val.get("candidate_correct",0)>0)
        if gate: pass_games.append(g)
        games[g]={"mode":MODE,"fit":fit,"source_assisted_p5_p9":val,"gate_pass":gate}

    verdict="SOURCE_ASSISTED_METER_STABILITY_SIGNAL" if pass_games else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r308-meter4-frozen-replay/1","rung":RUNG,
      "lineage":{"r307_run":35827692947,"r307_head":"03affec38439dab0aad126aa0004c2a3c96e8f2b","candidate_game_mode_pairs_frozen_before_p5_p9":True},
      "frozen_mode":MODE,"frozen_games":sorted(GAMES),
      "protocol":{"fit":"p0-p4 only","source_assisted_replay":"p5-p9 only","p10_p19_staged_or_read":False,"p5_p9_updates_selector":False,"p5_p9_updates_model":False,"promotion_scope":"representation primitive only"},
      "games":games,"pass_games":pass_games,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_replay_is_source_assisted":True,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r308":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"pass_games":pass_games,"games":games},sort_keys=True))

if __name__=="__main__": main()
