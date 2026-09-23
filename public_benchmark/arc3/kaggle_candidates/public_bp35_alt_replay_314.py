#!/usr/bin/env python3
"""R314: source-assisted alternate replay for bp35 after R308 meter instability.

R307 p0-p4 LOTO had three pre-existing zero-wrong exact-frame candidates:
  meter 18/18, regions 13/13, ui_mask 5/5.
R308 replayed the best meter candidate on p5-p9 and found 9 correct/5 wrong.
R314 now replays the OTHER pre-existing R307 candidates (regions, ui_mask) on
p5-p9, fitting p0-p4 only and preserving exact-baseline precedence.

This is explicitly source-assisted model selection after p5-p9 has already been
observed in the project. It is not independent generalization. p10-p19 are
forbidden and no solver/Kaggle claim is allowed.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_remaining6_exactframe_loto_307 as r307

RUNG=314
GAME="bp35-0a0ad940"
MODES=("regions","ui_mask")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(10)): raise SystemExit("exact p0-p9 required")
    train=[r for p in ps[:5] for r in r251.prepare_rows([p])]
    replay=[r for p in ps[5:] for r in r251.prepare_rows([p])]
    exact=r307.fit_exact(train)

    modes={}; zero=[]
    for m in MODES:
        tab,fit=r307.fit_abs(train,m)
        ev=r307.evaluate(replay,exact,tab,m)
        modes[m]={"fit":fit,"source_assisted_p5_p9":ev}
        if ev.get("candidate_predictions",0)>0 and ev.get("candidate_wrong",0)==0 and ev.get("candidate_correct",0)>0:
            zero.append(m)
    best=max(zero,key=lambda m:(modes[m]["source_assisted_p5_p9"].get("candidate_correct",0),modes[m]["source_assisted_p5_p9"].get("candidate_predictions",0))) if zero else None
    verdict="SOURCE_ASSISTED_ALTERNATE_ZERO_WRONG_SIGNAL" if best else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r314-bp35-alt-replay/1","rung":RUNG,"game":GAME,
      "lineage":{"r307_run":35827692947,"r307_preexisting_zero_wrong_candidates":{"meter":"18/18","regions":"13/13","ui_mask":"5/5"},"r308_meter_replay":"9 correct/5 wrong; rejected"},
      "protocol":{"fit":"p0-p4 only","source_assisted_replay":"p5-p9 only","candidate_family":"pre-existing R307 regions/ui_mask alternatives","p10_p19_staged_or_read":False,"selection_is_source_assisted":True,"promotion_scope":"public-development representation primitive only"},
      "modes":modes,"zero_wrong_modes":zero,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_replay_is_source_assisted":True,"p5_p9_already_observed_before_r314":True,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"solver_promotion":False,"whole_game_policy_claim":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r314":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))

if __name__=="__main__": main()
