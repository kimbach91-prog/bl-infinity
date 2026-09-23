#!/usr/bin/env python3
"""R330: nested training-only reliability gate over the fixed R327 structural method.

R329 froze one method and swept all 25 public games using p0-p4 LOTO:
5 games were zero-false; 15 had positive gain with false changes; 5 had no signal.
R330 does not choose a new representation per game. It keeps the exact R327
method and adds one generic reliability rule inside each OUTER p0-p4 fold:

For each structural template learned from the four outer-training traces,
require the exact same (seed key, residual template) to make >=2 firings on
>=2 INNER held training traces with ZERO wrong firings under nested
leave-one-training-trace-out evaluation. Only then may it act on the outer held
trace. Identity remains the fallback.

This is a public p0-p4-only falsifier/repair. p5-p19 are never staged/read.
"""
from __future__ import annotations

import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_seeded_structural_loto_327 as r327

RUNG=330
BASE_MODE="delta"
GRID=8
MIN_INNER_FIRINGS=2
MIN_INNER_HELD_TRACES=2


def firing_stats(prepared_rows, templates):
    stats=defaultdict(Counter)
    for row in prepared_rows:
        b,a,keys=row["b"],row["a"],row["keys"]
        h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=keys[r][c]
                rel=templates.get(k)
                if rel is None:
                    continue
                ok=True
                for dr,dc,before,after in rel:
                    rr,cc=r+dr,c+dc
                    if not (0<=rr<h and 0<=cc<w and int(b[rr][cc])==int(before)):
                        ok=False
                        break
                if not ok:
                    continue
                ident=(k,rel)
                stats[ident]["firings"]+=1
                wrong_cells=0; true_cells=0
                for dr,dc,before,after in rel:
                    rr,cc=r+dr,c+dc
                    av=int(a[rr][cc]); bv=int(b[rr][cc]); pv=int(after)
                    if pv==av and bv!=av:
                        true_cells+=1
                    elif pv!=av:
                        wrong_cells+=1
                stats[ident]["true_changed_correct"]+=true_cells
                stats[ident]["false_cells"]+=wrong_cells
                if wrong_cells:
                    stats[ident]["wrong_firings"]+=1
                else:
                    stats[ident]["correct_firings"]+=1
    return stats


def nested_trust(outer_train):
    agg=defaultdict(Counter)
    held_support=defaultdict(set)
    for inner_held in range(len(outer_train)):
        subtrain=[outer_train[i] for i in range(len(outer_train)) if i!=inner_held]
        templates,_=r327.fit_templates(subtrain)
        st=firing_stats(outer_train[inner_held],templates)
        for ident,cnt in st.items():
            agg[ident].update(cnt)
            if cnt["firings"]>0:
                held_support[ident].add(inner_held)
    trusted={
        ident for ident,cnt in agg.items()
        if cnt["firings"]>=MIN_INNER_FIRINGS
        and cnt["wrong_firings"]==0
        and len(held_support[ident])>=MIN_INNER_HELD_TRACES
    }
    return trusted,{
        "observed_template_identities":len(agg),
        "trusted_template_identities":len(trusted),
        "inner_firings":sum(c["firings"] for c in agg.values()),
        "inner_wrong_firings":sum(c["wrong_firings"] for c in agg.values()),
        "required_min_firings":MIN_INNER_FIRINGS,
        "required_min_held_traces":MIN_INNER_HELD_TRACES,
    }


def run_game(paths):
    game=r246.game_id(paths[0])
    traces=[r302.augment_trace(p) for p in paths]
    prepared=[r321.prep(t,BASE_MODE,GRID) for t in traces]
    base_total=Counter(); nested_total=Counter(); folds=[]
    for held in range(5):
        train=[prepared[i] for i in range(5) if i!=held]
        outer_templates,outer_fit=r327.fit_templates(train)
        base_ev=r327.evaluate(prepared[held],outer_templates)

        trusted,nested_fit=nested_trust(train)
        filtered={
            k:rel for k,rel in outer_templates.items()
            if (k,rel) in trusted
        }
        nested_ev=r327.evaluate(prepared[held],filtered)
        folds.append({
            "held_trace":held,
            "outer_fit":outer_fit,
            "nested_fit":nested_fit,
            "outer_templates":len(outer_templates),
            "trusted_outer_templates":len(filtered),
            "baseline_eval":base_ev,
            "nested_eval":nested_ev,
        })
        for k,v in base_ev.items():
            if isinstance(v,int): base_total[k]+=v
        for k,v in nested_ev.items():
            if isinstance(v,int): nested_total[k]+=v

    for total in (base_total,nested_total):
        total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
        total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]

    n=dict(nested_total); b=dict(base_total)
    if n.get("predicted_changes",0)>0 and n.get("false_changes",0)==0 and n.get("pixel_gain",0)>0 and n.get("exact_frame_gain",0)>0:
        verdict="NESTED_ZERO_FALSE_EXACTFRAME_SIGNAL"
    elif n.get("predicted_changes",0)>0 and n.get("false_changes",0)==0 and n.get("pixel_gain",0)>0:
        verdict="NESTED_ZERO_FALSE_PIXEL_SIGNAL"
    elif n.get("pixel_gain",0)>0:
        verdict="NESTED_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="NESTED_NO_SIGNAL"
    return game,b,n,folds,verdict


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--game",required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if not ps or any(r246.game_id(p)!=a.game for p in ps):
        raise SystemExit(f"exact game required: {a.game}")
    if [r246.pnum(p) for p in ps]!=list(range(5)):
        raise SystemExit("exact p0-p4 required")

    game,baseline,nested,folds,verdict=run_game(ps)
    out={
      "schema":"deus/arc3-r330-structural25-nested-reliability/1",
      "rung":RUNG,
      "game":game,
      "freeze":{
        "representation_method":"R327 fixed structural method",
        "method_source":"8d54bd197ae805a306493d5630c11268fcbe1ef9",
        "reliability_delta":"generic nested training-only zero-wrong template gate",
        "base_mode":BASE_MODE,
        "grid":GRID,
        "per_game_representation_selection":False,
      },
      "protocol":{
        "data":"public p0-p4 only",
        "outer_evaluation":"5-fold leave-one-trace-out",
        "inner_reliability":"nested leave-one-training-trace-out",
        "min_inner_firings":MIN_INNER_FIRINGS,
        "min_inner_held_traces":MIN_INNER_HELD_TRACES,
        "p5_p9_staged_or_read":False,
        "p10_p19_staged_or_read":False,
      },
      "r329_equivalent_baseline":baseline,
      "nested_loto":nested,
      "folds":folds,
      "verdict":verdict,
      "truth":{
        "public_trace_only":True,
        "source_free_runtime_logic":True,
        "p5_p9_read":False,
        "p10_p19_read":False,
        "independent_hidden_generalization_claim":False,
        "whole_game_solver_promotion":False,
        "kaggle_execution":False,
        "competition_submission":False,
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":game,"verdict":verdict,"baseline":baseline,"nested":nested},sort_keys=True))

if __name__=="__main__":
    main()
