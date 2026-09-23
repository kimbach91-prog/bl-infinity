#!/usr/bin/env python3
"""R311: source-assisted m0r0 exact-nodes p10-p19 alias-repair gate.

Prior public-development R277 localized the single coarse-state R276 error to a
coarse alias. R303 then showed nodes_exact and nodes_coarse are equivalent and
zero-wrong under p0-p4 internal LOTO. R311 therefore tests a materially more
specific before-state identity on reused-public p10-p19.

The hypothesis is source-assisted by the known R277 mismatch. It is not
independent generalization. Selector/model are not updated from p10-p19.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_exact_topology_loto_303 as r303

RUNG=311
GAME="m0r0-492f87ba"
MODE="nodes_exact"
BASELINE="nodes_coarse"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise SystemExit(f"exact p0-p19 required, got {nums}")
    fit=[r278.annotated_rows([p]) for p in ps[:10]]
    hold=[r for p in ps[10:] for r in r278.annotated_rows([p])]
    ctab,cfit=r303.fit(fit,MODE); btab,bfit=r303.fit(fit,BASELINE)
    cand=r303.evaluate(hold,ctab,MODE); base=r303.evaluate(hold,btab,BASELINE)
    passed=bool(cand.get("predictions",0)>0 and cand.get("wrong",0)==0 and cand.get("correct",0)>=base.get("correct",0))
    verdict="SOURCE_ASSISTED_EXACT_NODES_ZERO_WRONG_SIGNAL" if passed else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r311-m0r0-exact-nodes-p10p19/1","rung":RUNG,"game":GAME,
      "selector":{"mode":MODE,"baseline":BASELINE,"source_assisted_by_r277_error":True},
      "lineage":{"r276":"canon_nodes_ui p10-p19 1484/1485, one wrong","r277":"coarse-state alias diagnosed at p12 row66","r303":"p0-p4 LOTO nodes_exact 851/851 and nodes_coarse 851/851"},
      "protocol":{"refit":"p0-p9","evaluation":"p10-p19 reused public development","p10_p19_updates_selector":False,"p10_p19_updates_representation":False,"p10_p19_updates_model":False,"promotion_scope":"source-assisted public representation signal only"},
      "candidate_fit":cfit,"baseline_fit":bfit,"candidate":cand,"baseline":base,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"selector_is_source_assisted":True,"reused_public_development_holdout":True,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r311":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"candidate":cand,"baseline":base},sort_keys=True))
if __name__=="__main__": main()
