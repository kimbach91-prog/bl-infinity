#!/usr/bin/env python3
"""R174: prior-only structural screen-fixed selector for vertical world transport.

R173 showed 82% of R172's wrong cells were world->fixed mistakes. This rung
changes representation: learn screen-fixed vs shifted-world labels from prior
outcomes by value-pair / coarse structural features shared across coordinates,
not an absolute (row,col) mask. Each selector is evaluated prequentially on
exact-state cache misses. Current outcome is ingested only after prediction.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172

RUNG=174
MIN_LABEL_SUPPORT=3
MIN_PRIOR_FRAME_OK=2
FAMILIES=("pair","pair_band")
FALLBACKS=("fixed","world")

def unique(bank:Counter[str], support:int=1):
    if len(bank)!=1:return None
    k,n=next(iter(bank.items())); return k if n>=support else None

def band(i:int,n:int)->str:
    if i<3:return "edge0"
    if i<6:return "edge1"
    if i>=n-3:return "edge0r"
    if i>=n-6:return "edge1r"
    return "mid"

def feat(family:str, action:str, before, r:int,c:int,sr:int,sc:int):
    pair=(action,before[r][c],before[sr][sc])
    if family=="pair": return pair
    return pair+(band(r,len(before)),band(c,len(before[0])))

def render(before, shift, labels, family, action, fallback):
    dr,dc=shift; h,w=len(before),len(before[0]); out=[x[:] for x in before]
    for r in range(h):
      for c in range(w):
        sr,sc=r-dr,c-dc
        if not (0<=sr<h and 0<=sc<w): continue
        fixed,world=before[r][c],before[sr][sc]
        if fixed==world: out[r][c]=fixed; continue
        key=feat(family,action,before,r,c,sr,sc)
        lab=unique(labels[key],MIN_LABEL_SUPPORT)
        if lab is None: lab=fallback
        out[r][c]=fixed if lab=="fixed" else world
    return out

def learn_labels(before,after,shift,labels,family,action):
    dr,dc=shift; h,w=len(before),len(before[0])
    for r in range(h):
      for c in range(w):
        sr,sc=r-dr,c-dc
        if not (0<=sr<h and 0<=sc<w): continue
        fixed,world=before[r][c],before[sr][sc]
        if fixed==world: continue
        a=after[r][c]
        if a==fixed and a!=world: lab="fixed"
        elif a==world and a!=fixed: lab="world"
        else: continue
        labels[feat(family,action,before,r,c,sr,sc)][lab]+=1

def audit_trace(events:list[dict[str,Any]]):
    exact=defaultdict(Counter); shifts=defaultdict(Counter)
    labels={f:defaultdict(Counter) for f in FAMILIES}
    shadow=defaultdict(lambda:Counter())
    stats=defaultdict(Counter); pre=events[0]
    for e in events[1:]:
      if e.get("type")!="action": pre=e; continue
      before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
      if len(before)!=len(after) or len(before[0])!=len(after[0]): continue
      ek=r160.context_exact(before,action); prog=unique(exact[ek],1) if ek in exact else None
      pred_exact=r160.apply_program(before,prog) if prog else None
      sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None
      if pred_exact is None and sh is not None:
        for fam in FAMILIES:
          for fb in FALLBACKS:
            name=f"{fam}__fallback_{fb}"; pred=render(before,sh,labels[fam],fam,action,fb)
            stats[name]["raw"]+=1
            ok=pred==after
            stats[name]["raw_correct" if ok else "raw_wrong"]+=1
            q=shadow[(name,action)]["ok"]>=MIN_PRIOR_FRAME_OK and shadow[(name,action)]["wrong"]==0
            if q:
              stats[name]["qualified"]+=1
              stats[name]["qualified_correct" if ok else "qualified_wrong"]+=1
            shadow[(name,action)]["ok" if ok else "wrong"]+=1
      exact[ek][r160.program(before,after)]+=1
      if action in r172.CAMERA_ACTIONS:
        changed=sum(before[r][c]!=after[r][c] for r in range(len(before)) for c in range(len(before[0])))
        if changed:
          b=r167.best_nonzero_shift(before,after)
          if float(b["valid_match_fraction"])>=r172.MIN_TRANSITION_FIT:
            obs=(int(b["dr"]),int(b["dc"])); shifts[action][obs]+=1
            for fam in FAMILIES: learn_labels(before,after,obs,labels[fam],fam,action)
    out={}
    for n,c in stats.items():
      d={k:int(c[k]) for k in ["raw","raw_correct","raw_wrong","qualified","qualified_correct","qualified_wrong"]}
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      out[n]=d
    return out

def run(paths):
    parts=[audit_trace(base.load_events(p)) for p in paths]
    names=sorted(set().union(*(p.keys() for p in parts))); agg={}
    for n in names:
      d={k:sum(p.get(n,{}).get(k,0) for p in parts) for k in ["raw","raw_correct","raw_wrong","qualified","qualified_correct","qualified_wrong"]}
      d["per_trace_raw_correct"]=[p.get(n,{}).get("raw_correct",0) for p in parts]
      d["per_trace_raw_wrong"]=[p.get(n,{}).get("raw_wrong",0) for p in parts]
      d["per_trace_qualified_correct"]=[p.get(n,{}).get("qualified_correct",0) for p in parts]
      d["per_trace_qualified_wrong"]=[p.get(n,{}).get("qualified_wrong",0) for p in parts]
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      d["strict_p0_p10_gain"]=bool(d["qualified_wrong"]==0 and len(parts)>=2 and d["per_trace_qualified_correct"][0]>0 and d["per_trace_qualified_correct"][1]>0)
      agg[n]=d
    best=max(names,key=lambda n:(agg[n]["qualified_correct"],agg[n]["raw_correct"],-agg[n]["raw_wrong"])) if names else None
    strict=[n for n in names if agg[n]["strict_p0_p10_gain"]]
    return {"schema":"deus/arc3-public-structural-fixed-selector/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_STRUCTURAL_SCREEN_FIXED_SELECTOR_FULLFRAME_DIAGNOSTIC",
      "representation_change_from_rung173":{"changed":True,"change":"replace absolute screen coordinate mask with coordinate-shared value-pair/coarse-band fixed-vs-world selector learned from prior outcomes"},
      "source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},
      "parameters":{"min_label_support":MIN_LABEL_SUPPORT,"min_prior_frame_ok":MIN_PRIOR_FRAME_OK,"families":list(FAMILIES),"fallbacks":list(FALLBACKS)},
      "aggregate":{"selectors":agg,"best_diagnostic_selector":best,"strict_p0_p10_selectors":strict,"per_trace":parts},
      "diagnostic_gate":"ZERO_ERROR_P0_P10_STRUCTURAL_SELECTOR_GAIN" if strict else "NO_STRICT_PREQUENTIAL_STRUCTURAL_SELECTOR_GAIN",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"gpu_execution":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    if not a.input: raise SystemExit("input required")
    d=run(a.input); s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
