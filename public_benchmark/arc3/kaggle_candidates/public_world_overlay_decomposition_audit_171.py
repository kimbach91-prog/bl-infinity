#!/usr/bin/env python3
"""Rung 171: outcome-assisted world/overlay/boundary decomposition.

R170 showed that revisiting a latent camera place is not enough to recover the
full rendered frame. This audit decomposes reliable vertical-scroll transitions
into four effect channels: shifted-world transport, incoming boundary, screen-
fixed residual, and dynamic residual. It is structural research only and makes
no pre-action prediction.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_executable_world_model_134 as base
import public_dense_scroll_renderer_audit_167 as r167

RUNG=171
MIN_FIT=.95
CAMERA_ACTIONS={"UP","DOWN"}
Grid=list[list[int]]

def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    agg=Counter(); per_action=defaultdict(Counter); examples=[]
    pre=events[0]
    for e in events[1:]:
        if e.get("type")!="action": pre=e; continue
        before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
        if action not in CAMERA_ACTIONS or len(before)!=len(after) or len(before[0])!=len(after[0]): continue
        changed=sum(before[r][c]!=after[r][c] for r in range(len(before)) for c in range(len(before[0])))
        if not changed: continue
        best=r167.best_nonzero_shift(before,after)
        if float(best["valid_match_fraction"])<MIN_FIT: continue
        dr,dc=int(best["dr"]),int(best["dc"]); h,w=len(before),len(before[0])
        c=Counter(transitions=1,total_cells=h*w)
        for r in range(h):
            for col in range(w):
                sr,sc=r-dr,col-dc
                if not (0<=sr<h and 0<=sc<w):
                    c["incoming_boundary"]+=1
                    if after[r][col]==before[r][col]: c["incoming_screen_preserved"]+=1
                    continue
                if after[r][col]==before[sr][sc]:
                    c["shifted_world"]+=1
                elif after[r][col]==before[r][col]:
                    c["screen_fixed_residual"]+=1
                else:
                    c["dynamic_residual"]+=1
        agg.update(c); per_action[action].update(c)
        if len(examples)<12:
            examples.append({"action":action,"shift":[dr,dc],"fit":best["valid_match_fraction"],"counts":dict(c)})
    return {"aggregate":dict(agg),"per_action":{k:dict(v) for k,v in sorted(per_action.items())},"examples":examples}

def enrich(c:dict[str,int])->dict[str,Any]:
    out=dict(c); valid=c.get("shifted_world",0)+c.get("screen_fixed_residual",0)+c.get("dynamic_residual",0)
    residual=c.get("screen_fixed_residual",0)+c.get("dynamic_residual",0)
    out["valid_shifted_world_fraction"]=round(c.get("shifted_world",0)/valid,6) if valid else None
    out["residual_screen_fixed_fraction"]=round(c.get("screen_fixed_residual",0)/residual,6) if residual else None
    inc=c.get("incoming_boundary",0)
    out["incoming_screen_preserved_fraction"]=round(c.get("incoming_screen_preserved",0)/inc,6) if inc else None
    return out

def run(paths:list[Path])->dict[str,Any]:
    parts=[audit_trace(base.load_events(p)) for p in paths]
    total=Counter()
    action=defaultdict(Counter)
    for p in parts:
        total.update(p["aggregate"])
        for a,c in p["per_action"].items(): action[a].update(c)
    ag=enrich(dict(total)); pa={a:enrich(dict(c)) for a,c in sorted(action.items())}
    shifted=ag.get("valid_shifted_world_fraction") or 0
    screen=ag.get("residual_screen_fixed_fraction")
    recommendation=("WORLD_TRANSPORT_PLUS_EXPLICIT_OVERLAY_AND_BOUNDARY_RENDERER" if shifted>=.95 else "GENERAL_DENSE_RENDERER")
    return {
      "schema":"deus/arc3-public-world-overlay-decomposition-audit/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_OUTCOME_ASSISTED_WORLD_OVERLAY_DECOMPOSITION",
      "representation_change_from_rung170":{"changed":True,"change":"split reliable vertical scroll frames into shifted-world transport, incoming boundary, screen-fixed residual, and dynamic residual instead of caching full frame by latent camera place"},
      "source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},
      "aggregate":ag,"per_action":pa,"per_trace":parts,
      "diagnostic_gate":"WORLD_OVERLAY_BOUNDARY_STRUCTURE_CHARACTERIZED",
      "recommendation":recommendation,
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"outcome_assisted_analysis":True,"preoutcome_prediction_made":False,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"gpu_execution":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    if not a.input: raise SystemExit("at least one --input required")
    d=run(a.input); txt=json.dumps(d,indent=2,sort_keys=True)+"\n"
    if a.output: a.output.write_text(txt,encoding="utf-8")
    print(txt,end=""); return 0
if __name__=="__main__": raise SystemExit(main())
