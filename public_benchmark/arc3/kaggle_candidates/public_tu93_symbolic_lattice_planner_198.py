#!/usr/bin/env python3
"""R198: TU93 symbolic lattice planner and transition classifier.

TU93 is a navigation game represented on a 64x64 pixel board. Public traces show:
- player = one 3x3 sprite with eight color-9 cells and one color-4 facing marker;
- empty room = 3x3 color-0 block;
- goal room = 3x3 color-14 block;
- hazard = 3x3 sprite with eight color-8 cells and one color-15 marker;
- open connector = 3x3 color-2 block;
- walls/background = color-5;
- HUD/timer is the bottom row and is excluded from gameplay-state equality.

Rooms live on a 6-cell lattice and connectors occupy the interleaving 3x3 blocks.
This solver is deterministic and train-free: parse the current visible board,
build the room graph, avoid hazards, and BFS to the goal. It also predicts the
outcome class of each observed action from PRE-action board only:
MOVE / BLOCKED / HAZARD / GOAL.

This is public-game behavioral evidence. It does not claim hidden-game
generalization, Kaggle execution, or leaderboard score.
"""
from __future__ import annotations
import argparse,json,re
from collections import deque,Counter
from pathlib import Path
from typing import Any

GAME="tu93-0768757b"
RUNG=198
DIRS={"UP":(-1,0),"DOWN":(1,0),"LEFT":(0,-1),"RIGHT":(0,1)}
Grid=list[list[int]]


def load_events(path:Path):
    out=[]
    for raw in path.read_text().splitlines():
        if not raw.strip(): continue
        x=json.loads(raw)
        if isinstance(x,dict) and isinstance(x.get("board"),list):out.append(x)
    return out


def window(g:Grid,r:int,c:int,h:int=3,w:int=3):
    if r<0 or c<0 or r+h>len(g) or c+w>len(g[0]):return None
    return [row[c:c+w] for row in g[r:r+h]]


def flat(w):return [v for row in w for v in row] if w is not None else []


def is_player(w):
    x=Counter(flat(w));return len(flat(w))==9 and x[9]==8 and x[4]==1


def is_hazard(w):
    x=Counter(flat(w));return len(flat(w))==9 and x[8]==8 and x[15]==1


def is_uniform(w,v):
    x=flat(w);return len(x)==9 and all(z==v for z in x)


def find_unique_sprite(g:Grid,pred):
    hits=[]
    for r in range(0,len(g)-2):
        for c in range(0,len(g[0])-2):
            w=window(g,r,c)
            if pred(w):hits.append((r,c))
    # 3x3 exact sprite only matches at its aligned top-left because shifted windows
    # include surrounding cells. Still fail closed if ambiguous.
    return hits[0] if len(hits)==1 else None


def find_goals(g:Grid):
    hits=[]
    for r in range(0,len(g)-2):
        for c in range(0,len(g[0])-2):
            if is_uniform(window(g,r,c),14):hits.append((r,c))
    # Collapse overlapping hits inside a larger same-color region; TU93 goals are 3x3.
    uniq=[]
    for p in hits:
        if not any(abs(p[0]-q[0])<3 and abs(p[1]-q[1])<3 for q in uniq):uniq.append(p)
    return uniq


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
    cr=r+3*dr;cc=c+3*dc
    return is_uniform(window(g,cr,cc),2)


def destination(r:int,c:int,action:str):
    dr,dc=DIRS[action];return r+6*dr,c+6*dc


def predicted_outcome(g:Grid,action:str):
    if action not in DIRS:return "OTHER",None
    p=find_unique_sprite(g,is_player)
    if p is None:return "NO_PLAYER",None
    r,c=p;dr,dc=DIRS[action]
    if not corridor_open(g,r,c,dr,dc):return "BLOCKED",p
    nr,nc=destination(r,c,action)
    typ=cell_type(g,nr,nc)
    if typ=="GOAL":return "GOAL",(nr,nc)
    if typ=="HAZARD":return "HAZARD",(nr,nc)
    if typ=="EMPTY":return "MOVE",(nr,nc)
    return "BLOCKED",(nr,nc)


def observed_outcome(before:dict[str,Any],after:dict[str,Any]):
    if int(after.get("level",0))>int(before.get("level",0)) or int(after.get("score",0))>int(before.get("score",0)):
        return "GOAL"
    if str(after.get("state","")).upper() in {"GAME_OVER","LOST","FAILED"}:
        return "HAZARD"
    a=before["board"];b=after["board"]
    # exclude bottom timer/HUD row
    gameplay_changed=sum(a[r][c]!=b[r][c] for r in range(min(63,len(a))) for c in range(len(a[0])))
    return "MOVE" if gameplay_changed else "BLOCKED"


def graph(g:Grid):
    start=find_unique_sprite(g,is_player)
    goals=set(find_goals(g))
    if start is None:return None,goals,{}
    q=deque([start]);seen={start};edges={}
    while q:
        r,c=q.popleft();edges[(r,c)]={}
        for action,(dr,dc) in DIRS.items():
            if not corridor_open(g,r,c,dr,dc):continue
            nr,nc=destination(r,c,action);typ=cell_type(g,nr,nc)
            if (nr,nc) in goals:typ="GOAL"
            if typ in {"EMPTY","GOAL","PLAYER"}:
                edges[(r,c)][action]=(nr,nc)
                if (nr,nc) not in seen:
                    seen.add((nr,nc));q.append((nr,nc))
            elif typ=="HAZARD":
                edges[(r,c)][action]=("HAZARD",nr,nc)
    return start,goals,edges


def shortest_plan(g:Grid):
    start,goals,edges=graph(g)
    if start is None or not goals:return None
    q=deque([(start,[])])
    seen={start}
    while q:
        node,path=q.popleft()
        if node in goals:return path
        for action,nxt in edges.get(node,{}).items():
            if isinstance(nxt,tuple) and nxt and nxt[0]=="HAZARD":continue
            if nxt not in seen:
                seen.add(nxt);q.append((nxt,path+[action]))
    return None


def audit(paths:list[Path]):
    cm=Counter();per_trace=[];plan_stats=Counter();examples=[]
    for path in paths:
        events=load_events(path)
        pre=events[0]
        local=Counter()
        # Test every initial/reset/level-entry board for plan existence.
        for idx,e in enumerate(events):
            if not isinstance(e.get("board"),list):continue
            is_reset=(e.get("action_display")=="RESET")
            prev_level=events[idx-1].get("level") if idx>0 and isinstance(events[idx-1],dict) else None
            is_level_entry=idx==0 or (prev_level is not None and int(e.get("level",0))>int(prev_level))
            if is_reset or is_level_entry:
                p=shortest_plan(e["board"])
                plan_stats["states"]+=1
                if p is not None:
                    plan_stats["plan_found"]+=1;plan_stats["total_plan_length"]+=len(p)
                    if not p:plan_stats["already_goal"]+=1
                else:plan_stats["no_plan"]+=1
        for e in events[1:]:
            if e.get("type")!="action":
                pre=e;continue
            if e.get("action_display") not in DIRS:
                pre=e;continue
            pred,_=predicted_outcome(pre["board"],e["action_display"])
            obs=observed_outcome(pre,e)
            cm["tests"]+=1;local["tests"]+=1
            cm[f"pred:{pred}"]+=1;cm[f"obs:{obs}"]+=1
            if pred==obs:
                cm["correct"]+=1;local["correct"]+=1
            else:
                cm["wrong"]+=1;local["wrong"]+=1
                if len(examples)<20:examples.append({"file":path.name,"step":e.get("action_num"),"action":e["action_display"],"pred":pred,"obs":obs})
            pre=e
        per_trace.append({"file":path.name,"tests":int(local["tests"]),"correct":int(local["correct"]),"wrong":int(local["wrong"])})
    acc=cm["correct"]/cm["tests"] if cm["tests"] else 0.0
    plan_rate=plan_stats["plan_found"]/plan_stats["states"] if plan_stats["states"] else 0.0
    return {
      "schema":"deus/arc3-tu93-symbolic-lattice-planner/1",
      "rung":RUNG,"game":GAME,
      "transition_classifier":{
        "tests":int(cm["tests"]),"correct":int(cm["correct"]),"wrong":int(cm["wrong"]),
        "accuracy":round(acc,6),
        "pred_counts":{k.split(":",1)[1]:int(v) for k,v in cm.items() if k.startswith("pred:")},
        "obs_counts":{k.split(":",1)[1]:int(v) for k,v in cm.items() if k.startswith("obs:")},
        "mismatch_examples":examples,
        "per_trace":per_trace,
      },
      "planner":{
        "states":int(plan_stats["states"]),"plan_found":int(plan_stats["plan_found"]),"no_plan":int(plan_stats["no_plan"]),
        "plan_found_rate":round(plan_rate,6),
        "mean_plan_length":round(plan_stats["total_plan_length"]/plan_stats["plan_found"],3) if plan_stats["plan_found"] else None,
      },
      "diagnostic_gate":"TU93_SYMBOLIC_BEHAVIOR_SOLVER_PASS" if acc>=0.99 and plan_rate>=0.99 else "TU93_SYMBOLIC_BEHAVIOR_SOLVER_NEEDS_REPAIR",
      "truth":{
        "public_trace_only":True,
        "train_free_deterministic_parser":True,
        "preaction_only_outcome_prediction":True,
        "hud_timer_excluded_from_gameplay_outcome":True,
        "planner_avoids_visible_hazards":True,
        "full_game_runtime_execution":False,
        "hidden_game_generalization_claim":False,
        "kaggle_execution":False,
        "submission_quota_spent":False,
      }
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if not a.input:raise SystemExit("input required")
    d=audit(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"rung":RUNG,"gate":d["diagnostic_gate"],"classifier":d["transition_classifier"],"planner":d["planner"]},sort_keys=True))
    return 0 if d["diagnostic_gate"]=="TU93_SYMBOLIC_BEHAVIOR_SOLVER_PASS" else 3

if __name__=="__main__":raise SystemExit(main())
