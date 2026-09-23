#!/usr/bin/env python3
"""R308: forensic diagnostic for the two R306 cn04 graph_exact p10-p19 errors.

R306 froze graph_exact before p5-p9 and then observed 235 correct / 2 wrong on
reused-public p10-p19. R308 changes no predictor and makes no promotion. It
reproduces only those wrong predictions and asks whether causal phase or an 8x8
region discriminator separates the heldout target within the same frozen graph
state/action class.

Any future repair using this diagnostic is source-assisted by reused public
p10-p19 and must not be presented as independent generalization.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_relational_topology_diag_274 as r274
import public_subset4_exact_topology_loto_303 as r303

RUNG=308
GAME="cn04-2fe56bfb"
MODE="graph_exact"

def phase(row):
    p=row.get("phase_before",("START",0))
    if isinstance(p,list): p=tuple(p)
    return tuple(p) if isinstance(p,tuple) else (str(p),0)

def graph_key(row):
    return (r274.dig(r303.state(row,"before",MODE)),r275.action_class(row["action"]))

def target(row):
    return r274.dig(r303.state(row,"after",MODE))

def region_key(row):
    b=r303.canon(row["before"],row["action"])
    return r274.dig(r246.regions(b,G=8))

def deterministic(counter):
    return next(iter(counter)) if len(counter)==1 else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise SystemExit(f"exact p0-p19 required, got {nums}")

    fit_traces=[r278.annotated_rows([p]) for p in ps[:10]]
    fit=[r for tr in fit_traces for r in tr]
    hold=[]
    for p in ps[10:]:
        rr=r278.annotated_rows([p])
        for i,row in enumerate(rr):
            x=dict(row); x["_pnum"]=r246.pnum(p); x["_row"]=i; hold.append(x)

    tab,_=r303.fit(fit_traces,MODE)
    base_obs=defaultdict(Counter)
    raw_before=defaultdict(set)
    phase_obs=defaultdict(Counter)
    region_obs=defaultdict(Counter)
    combo_obs=defaultdict(Counter)
    for row in fit:
        k=graph_key(row); t=target(row)
        base_obs[k][t]+=1
        raw_before[k].add(r246.digest(row["before"]))
        phase_obs[(k,phase(row))][t]+=1
        region_obs[(k,region_key(row))][t]+=1
        combo_obs[(k,phase(row),region_key(row))][t]+=1

    mismatches=[]; stats=Counter()
    for row in hold:
        k=graph_key(row); pred=tab.get(k)
        if pred is None: continue
        stats["predictions"]+=1
        actual=target(row)
        if pred==actual:
            stats["correct"]+=1; continue
        stats["wrong"]+=1
        pk=(k,phase(row)); rk=(k,region_key(row)); ck=(k,phase(row),region_key(row))
        pdet=deterministic(phase_obs.get(pk,Counter()))
        rdet=deterministic(region_obs.get(rk,Counter()))
        cdet=deterministic(combo_obs.get(ck,Counter()))
        mismatches.append({
          "pnum":row["_pnum"],"trace_row":row["_row"],"action":row["action"],"phase":list(phase(row)),
          "train_base_support":sum(base_obs[k].values()),"train_distinct_raw_before":len(raw_before[k]),
          "held_region_key":region_key(row),
          "phase_seen":pk in phase_obs,"region_seen":rk in region_obs,"phase_region_seen":ck in combo_obs,
          "phase_deterministic_target":pdet,"region_deterministic_target":rdet,"phase_region_deterministic_target":cdet,
          "phase_would_correct":pdet==actual,"region_would_correct":rdet==actual,"phase_region_would_correct":cdet==actual,
          "predicted_target":pred,"actual_target":actual,
        })
    verdict="TWO_ERROR_DIAGNOSED" if len(mismatches)==2 else ("ERRORS_DIAGNOSED" if mismatches else "NO_ERROR_REPRODUCED")
    out={
      "schema":"deus/arc3-r308-cn04-two-error-diagnostic/1","rung":RUNG,"game":GAME,
      "lineage":{"r306_run":35827152916,"r306_job":107071289596,"r306_result":"235 correct / 2 wrong graph_exact on reused-public p10-p19"},
      "protocol":{"fit":"p0-p9 frozen graph_exact table","diagnostic":"p10-p19 wrong predictions only","predictor_modified":False,"future_hypothesis_may_use_diagnostic":True},
      "stats":dict(stats),"mismatch_count":len(mismatches),"mismatches":mismatches,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"reused_public_development_holdout":True,"diagnostic_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r308":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"stats":out["stats"],"mismatches":mismatches},sort_keys=True))
if __name__=="__main__": main()
