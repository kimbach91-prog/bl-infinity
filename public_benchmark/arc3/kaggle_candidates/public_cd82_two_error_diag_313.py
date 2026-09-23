#!/usr/bin/env python3
"""R313: forensic diagnostic for cd82 exact_nodes_to_coarse p10-p19 errors.

R309 observed exact_nodes_to_coarse at 588 correct / 2 wrong on reused-public
p10-p19. This diagnostic changes no predictor. For each of those two wrong
predictions, it checks whether exact graph or phase-conditioned exact nodes,
fit only on p0-p9, would abstain or select the actual coarse target.

Any later repair is source-assisted public development only.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_asymmetric_alias_loto_304 as r304

RUNG=313
GAME="cd82-fb555c5d"
BASE="exact_nodes_to_coarse"
ALT_MODES=("exact_graph_to_coarse","exact_nodes_phase_to_coarse")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise SystemExit(f"exact p0-p19 required, got {nums}")
    fit=[r278.annotated_rows([p]) for p in ps[:10]]
    hold=[]
    for p in ps[10:]:
        rr=r278.annotated_rows([p])
        for i,row in enumerate(rr):
            x=dict(row); x["_pnum"]=r246.pnum(p); x["_row"]=i; hold.append(x)
    base_tab,_=r304.fit(fit,BASE)
    alt_tabs={m:r304.fit(fit,m)[0] for m in ALT_MODES}
    mismatches=[]; stats={"predictions":0,"correct":0,"wrong":0}
    for row in hold:
        k=r304.before_key(row,BASE); pred=base_tab.get(k)
        if pred is None: continue
        stats["predictions"]+=1; actual=r304.target(row)
        if pred==actual:
            stats["correct"]+=1; continue
        stats["wrong"]+=1
        alts={}
        for m in ALT_MODES:
            p=alt_tabs[m].get(r304.before_key(row,m))
            alts[m]={"prediction":p,"would_correct":p==actual,"abstain":p is None}
        mismatches.append({"pnum":row["_pnum"],"trace_row":row["_row"],"action":row["action"],"predicted_target":pred,"actual_target":actual,"alternatives":alts})
    verdict="TWO_ERROR_DIAGNOSED" if len(mismatches)==2 else ("ERRORS_DIAGNOSED" if mismatches else "NO_ERROR_REPRODUCED")
    out={
      "schema":"deus/arc3-r313-cd82-two-error-diagnostic/1","rung":RUNG,"game":GAME,
      "lineage":{"r309_run":35827418910,"r309_result":"exact_nodes_to_coarse 588 correct / 2 wrong"},
      "protocol":{"fit":"p0-p9","diagnostic":"p10-p19 base mismatches only","predictor_modified":False,"future_hypothesis_may_use_diagnostic":True},
      "stats":stats,"mismatch_count":len(mismatches),"mismatches":mismatches,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"reused_public_development_holdout":True,"diagnostic_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r313":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"stats":stats,"mismatches":mismatches},sort_keys=True))
if __name__=="__main__": main()
