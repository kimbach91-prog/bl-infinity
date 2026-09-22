#!/usr/bin/env python3
"""R199: TU93 dynamic-hazard lattice classifier + safe-action planner.

Representation change from R198:
- keep the 6-cell room/corridor lattice;
- model hazards as dynamic agents rather than static destination tiles;
- use the color-15 marker position inside each hazard sprite as a heading/phase cue;
- learn marker->hazard displacement only from public p0-p9 traces;
- evaluate p10-p19 only, with current outcomes hidden until after prediction;
- treat a blocked player as still vulnerable to a hazard moving onto its cell;
- expose a one-step safe-action planner under partial observability rather than
  falsely requiring the visible viewport to already contain a complete goal path.

This is same-game public heldout behavioral evidence, not hidden-game
independent generalization, Kaggle execution, competition submission, or score.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

GAME = "tu93-0768757b"
RUNG = 199
DIRS = {"UP":(-1,0),"DOWN":(1,0),"LEFT":(0,-1),"RIGHT":(0,1)}
Grid = list[list[int]]


def load_events(path: Path):
    out=[]
    for raw in path.read_text().splitlines():
        if not raw.strip():
            continue
        x=json.loads(raw)
        if isinstance(x,dict) and isinstance(x.get("board"),list):
            out.append(x)
    return out


def trace_index(path: Path):
    m=re.search(r"_p(\d+)_", path.name)
    return int(m.group(1)) if m else -1


def window(g:Grid,r:int,c:int,h:int=3,w:int=3):
    if r<0 or c<0 or r+h>len(g) or c+w>len(g[0]):
        return None
    return [row[c:c+w] for row in g[r:r+h]]


def flat(w):
    return [v for row in w for v in row] if w is not None else []


def is_player(w):
    x=Counter(flat(w));return len(flat(w))==9 and x[9]==8 and x[4]==1


def is_hazard(w):
    x=Counter(flat(w));return len(flat(w))==9 and x[8]==8 and x[15]==1


def is_uniform(w,v):
    x=flat(w);return len(x)==9 and all(z==v for z in x)


def marker_offset(w, marker:int):
    if w is None:return None
    hits=[(r,c) for r,row in enumerate(w) for c,v in enumerate(row) if v==marker]
    return hits[0] if len(hits)==1 else None


def find_unique_sprite(g:Grid,pred):
    hits=[]
    for r in range(0,len(g)-2):
        for c in range(0,len(g[0])-2):
            if pred(window(g,r,c)):
                hits.append((r,c))
    return hits[0] if len(hits)==1 else None


def find_hazards(g:Grid):
    hits=[]
    for r in range(0,len(g)-2):
        for c in range(0,len(g[0])-2):
            w=window(g,r,c)
            if is_hazard(w):
                hits.append({"pos":(r,c),"marker":marker_offset(w,15)})
    return hits


def cell_type(g:Grid,r:int,c:int):
    w=window(g,r,c)
    if w is None:return "OOB"
    if is_player(w):return "PLAYER"
    if is_hazard(w):return "HAZARD"
    if is_uniform(w,0):return "EMPTY"
    if is_uniform(w,14):return "GOAL"
    if is_uniform(w,5):return "WALL"
    return "OTHER"


def corridor_open(g:Grid,r:int,c:int,dr:int,dc:int):
    return is_uniform(window(g,r+3*dr,c+3*dc),2)


def destination(r:int,c:int,action:str):
    dr,dc=DIRS[action];return r+6*dr,c+6*dc


def observed_outcome(before:dict[str,Any], after:dict[str,Any]):
    if int(after.get("level",0))>int(before.get("level",0)) or int(after.get("score",0))>int(before.get("score",0)):
        return "GOAL"
    if str(after.get("state","")).upper() in {"GAME_OVER","LOST","FAILED"}:
        return "HAZARD"
    a=before["board"];b=after["board"]
    gameplay_changed=sum(a[r][c]!=b[r][c] for r in range(min(63,len(a))) for c in range(len(a[0])))
    return "MOVE" if gameplay_changed else "BLOCKED"


def match_hazards(before, after, max_manhattan=12):
    """Nearest one-to-one match used only to estimate public-train dynamics."""
    pairs=[]; used=set()
    for hb in before:
        br,bc=hb["pos"]
        cand=[]
        for j,ha in enumerate(after):
            if j in used:continue
            ar,ac=ha["pos"]
            d=abs(ar-br)+abs(ac-bc)
            if d<=max_manhattan:
                cand.append((d,j,ha))
        if cand:
            _,j,ha=min(cand,key=lambda x:(x[0],x[1]))
            used.add(j);pairs.append((hb,ha))
    return pairs


def learn_marker_motion(train_paths:list[Path]):
    counts=defaultdict(Counter)
    samples=Counter()
    for path in train_paths:
        events=load_events(path)
        pre=events[0] if events else None
        for e in events[1:]:
            if pre is None:
                pre=e;continue
            if e.get("type")!="action" or e.get("action_display") not in DIRS:
                pre=e;continue
            bh=find_hazards(pre["board"]); ah=find_hazards(e["board"])
            for hb,ha in match_hazards(bh,ah):
                marker=hb["marker"]
                if marker is None:continue
                br,bc=hb["pos"]; ar,ac=ha["pos"]
                delta=(ar-br,ac-bc)
                # keep local agent motion only; resets/teleports are excluded
                if abs(delta[0])+abs(delta[1])<=12:
                    counts[marker][delta]+=1;samples[marker]+=1
            pre=e
    model={}
    diagnostics={}
    for marker,c in counts.items():
        total=sum(c.values()); delta,n=c.most_common(1)[0]
        model[marker]=delta
        diagnostics[str(marker)]={
            "support":total,"majority_delta":list(delta),"confidence":round(n/total,6),
            "distribution":{str(k):int(v) for k,v in c.items()}
        }
    return model,diagnostics


def predict_hazard_positions(g:Grid, motion_model):
    out=[]
    for h in find_hazards(g):
        r,c=h["pos"]
        dr,dc=motion_model.get(h["marker"],(0,0))
        nr,nc=r+dr,c+dc
        if 0<=nr<len(g)-2 and 0<=nc<len(g[0])-2:
            out.append((nr,nc))
        else:
            out.append((r,c))
    return out


def predicted_outcome(g:Grid, action:str, motion_model):
    if action not in DIRS:return "OTHER",None
    p=find_unique_sprite(g,is_player)
    if p is None:return "NO_PLAYER",None
    r,c=p;dr,dc=DIRS[action]
    open_=corridor_open(g,r,c,dr,dc)
    player_post=(r,c) if not open_ else destination(r,c,action)
    predicted_haz=set(predict_hazard_positions(g,motion_model))
    current_haz={h["pos"] for h in find_hazards(g)}
    # dynamic collision includes hazard moving onto a blocked/stationary player,
    # player landing on predicted hazard location, and head-on lattice swaps.
    collision=player_post in predicted_haz
    if open_:
        collision = collision or (player_post in current_haz and (r,c) in predicted_haz)
    if collision:return "HAZARD",player_post
    if not open_:return "BLOCKED",player_post
    typ=cell_type(g,*player_post)
    if typ=="GOAL":return "GOAL",player_post
    if typ in {"EMPTY","PLAYER","HAZARD"}:return "MOVE",player_post
    return "BLOCKED",player_post


def safe_actions(g:Grid,motion_model):
    p=find_unique_sprite(g,is_player)
    if p is None:return []
    out=[]
    for a in DIRS:
        pred,_=predicted_outcome(g,a,motion_model)
        if pred in {"MOVE","GOAL"}:out.append(a)
    return out


def evaluate(eval_paths:list[Path], motion_model):
    cm=Counter(); per_trace=[]; examples=[]; safe=Counter()
    for path in eval_paths:
        events=load_events(path)
        if not events:continue
        pre=events[0]; local=Counter()
        for e in events[1:]:
            if e.get("type")!="action" or e.get("action_display") not in DIRS:
                pre=e;continue
            acts=safe_actions(pre["board"],motion_model)
            safe["states"]+=1
            if acts:safe["available"]+=1
            pred,_=predicted_outcome(pre["board"],e["action_display"],motion_model)
            obs=observed_outcome(pre,e)
            cm["tests"]+=1;local["tests"]+=1
            cm[f"pred:{pred}"]+=1;cm[f"obs:{obs}"]+=1
            if pred==obs:
                cm["correct"]+=1;local["correct"]+=1
            else:
                cm["wrong"]+=1;local["wrong"]+=1
                if len(examples)<40:
                    examples.append({
                        "file":path.name,"step":e.get("action_num"),"action":e["action_display"],
                        "pred":pred,"obs":obs,"player":find_unique_sprite(pre["board"],is_player),
                        "hazards":find_hazards(pre["board"]),"predicted_hazards":predict_hazard_positions(pre["board"],motion_model)
                    })
            pre=e
        per_trace.append({"file":path.name,"tests":int(local["tests"]),"correct":int(local["correct"]),"wrong":int(local["wrong"])})
    acc=cm["correct"]/cm["tests"] if cm["tests"] else 0.0
    safe_rate=safe["available"]/safe["states"] if safe["states"] else 0.0
    return cm,per_trace,examples,safe,acc,safe_rate


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if not a.input:raise SystemExit("input required")
    paths=sorted(a.input,key=trace_index)
    train=[p for p in paths if 0<=trace_index(p)<=9]
    ev=[p for p in paths if 10<=trace_index(p)<=19]
    if len(train)!=10 or len(ev)!=10:raise SystemExit(f"expected p0-p19 split; got train={len(train)} eval={len(ev)}")
    model,motion_diag=learn_marker_motion(train)
    cm,per_trace,examples,safe,acc,safe_rate=evaluate(ev,model)
    gate="TU93_DYNAMIC_HAZARD_HELDOUT_PASS" if acc>=0.99 and safe_rate>=0.99 else "TU93_DYNAMIC_HAZARD_HELDOUT_NEEDS_REPAIR"
    d={
      "schema":"deus/arc3-tu93-dynamic-hazard-heldout/1","rung":RUNG,"game":GAME,
      "split":{"train":[p.name for p in train],"eval":[p.name for p in ev]},
      "motion_model":{"marker_to_delta":{str(k):list(v) for k,v in model.items()},"diagnostics":motion_diag},
      "heldout_classifier":{
        "tests":int(cm["tests"]),"correct":int(cm["correct"]),"wrong":int(cm["wrong"]),"accuracy":round(acc,6),
        "pred_counts":{k.split(":",1)[1]:int(v) for k,v in cm.items() if k.startswith("pred:")},
        "obs_counts":{k.split(":",1)[1]:int(v) for k,v in cm.items() if k.startswith("obs:")},
        "mismatch_examples":examples,"per_trace":per_trace,
      },
      "safe_action_planner":{"states":int(safe["states"]),"available":int(safe["available"]),"rate":round(safe_rate,6)},
      "diagnostic_gate":gate,
      "truth":{
        "public_same_game_train_traces_p0_p9":True,
        "public_same_game_heldout_traces_p10_p19":True,
        "current_eval_outcome_hidden_until_after_prediction":True,
        "dynamic_hazard_marker_representation":True,
        "partial_observability_safe_action_not_full_goal_plan":True,
        "full_game_runtime_execution":False,
        "hidden_game_independent_generalization_claim":False,
        "kaggle_execution":False,"submission_quota_spent":False,
      }
    }
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"rung":RUNG,"gate":gate,"motion_model":d["motion_model"],"classifier":{k:v for k,v in d["heldout_classifier"].items() if k not in ("mismatch_examples","per_trace")},"safe":d["safe_action_planner"],"mismatches":examples[:12]},sort_keys=True))
    return 0 if gate.endswith("PASS") else 3

if __name__=="__main__":raise SystemExit(main())
