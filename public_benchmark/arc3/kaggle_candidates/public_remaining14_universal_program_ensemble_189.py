#!/usr/bin/env python3
"""R189: universal executable-program ensemble for R184's remaining 14 families.

The frozen R180 camera-overlay family had zero applicability on these games.
R189 removes that representation restriction and predicts unseen exact states
from prior same-trace evidence using action-normalized executable programs:

  * identity with a coarse visible-state context,
  * R134 global/component translation and deterministic color-map programs,
  * R136 position-invariant local patch rewrites,
  * mouse/click-relative local patch rewrites,
  * dense viewport shift programs with either preserve-boundary or background
    fill semantics,
  * cyclic full-board shifts.

Exact visible-state/action memory remains the first lane. Program support and
reliability are updated only AFTER the current prediction is frozen/scored.
Multiple disagreeing qualified predictions fail closed by abstention.

This is public source-assisted prequential replay only, not Kaggle execution or
independent hidden-game generalization.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_dense_scroll_renderer_audit_167 as r167
import public_local_transition_program_prequential_136 as r136

RUNG = 189
TARGET_GAMES = (
    "bp35-0a0ad940","ft09-0d8bbf25","g50t-5849a774","lf52-271a04aa",
    "lp85-305b61c3","ls20-9607627b","m0r0-492f87ba","r11l-495a7899",
    "s5i5-18d95033","sb26-7fbdac44","su15-1944f8ab","tn36-ef4dde99",
    "tr87-cd924810","vc33-5430563c",
)
POLICIES = {
    "s2_shadow2": (2, 2),
    "s2_shadow1": (2, 1),
    "s2_noshadow": (2, 0),
    "s1_shadow1": (1, 1),
}
Grid = list[list[int]]


def action_key(action: str) -> str:
    return "MOUSE" if action.startswith("MOUSE(") else (action or "UNKNOWN")


def parse_mouse(action: str) -> tuple[int,int] | None:
    m = re.match(r"MOUSE\(row=(-?\d+),\s*col=(-?\d+)\)", action)
    return (int(m.group(1)), int(m.group(2))) if m else None


def coarse_context(board: Grid) -> dict[str, Any]:
    h,w=len(board),len(board[0])
    bg=base.dominant_background(board)
    counts=Counter(v for row in board for v in row)
    # Quantize counts so identity evidence can transfer across small state changes
    # without becoming globally unconditional.
    hist=sorted((int(k), int(v//4)*4) for k,v in counts.items())
    return {"h":h,"w":w,"bg":bg,"colors":len(counts),"hist4":hist}


def patch_with_bounds(board:Grid,r0:int,c0:int,r1:int,c1:int)->Grid:
    return [row[c0:c1+1] for row in board[r0:r1+1]]


def infer_mouse_patch(before:Grid, after:Grid, action:str) -> dict[str,Any] | None:
    click=parse_mouse(action)
    if click is None or not base.same_shape(before,after) or before==after:
        return None
    h,w=len(before),len(before[0])
    pts=[(r,c) for r in range(h) for c in range(w) if before[r][c]!=after[r][c]]
    if not pts:
        return None
    r0=max(0,min(r for r,_ in pts)-1); r1=min(h-1,max(r for r,_ in pts)+1)
    c0=max(0,min(c for _,c in pts)-1); c1=min(w-1,max(c for _,c in pts)+1)
    if r0==0 and c0==0 and r1==h-1 and c1==w-1:
        return None
    cr,cc=click
    return {
        "kind":"mouse_patch",
        "dr":r0-cr,"dc":c0-cc,
        "before_patch":patch_with_bounds(before,r0,c0,r1,c1),
        "after_patch":patch_with_bounds(after,r0,c0,r1,c1),
    }


def apply_mouse_patch(program:dict[str,Any], board:Grid, action:str)->Grid|None:
    click=parse_mouse(action)
    if click is None:
        return None
    pre=base.as_grid(program["before_patch"]); post=base.as_grid(program["after_patch"])
    if not base.same_shape(pre,post):
        return None
    cr,cc=click
    r0=cr+int(program["dr"]); c0=cc+int(program["dc"])
    ph,pw=len(pre),len(pre[0]); h,w=len(board),len(board[0])
    if r0<0 or c0<0 or r0+ph>h or c0+pw>w:
        return None
    for rr in range(ph):
        if board[r0+rr][c0:c0+pw]!=pre[rr]:
            return None
    out=[row[:] for row in board]
    for rr in range(ph):
        out[r0+rr][c0:c0+pw]=post[rr][:]
    return out


def apply_preserve_shift(board:Grid, dr:int, dc:int)->Grid:
    h,w=len(board),len(board[0]); out=[row[:] for row in board]
    for r in range(h):
        for c in range(w):
            sr,sc=r-dr,c-dc
            if 0<=sr<h and 0<=sc<w:
                out[r][c]=board[sr][sc]
    return out


def apply_bg_shift(board:Grid, dr:int, dc:int, bg:int)->Grid:
    h,w=len(board),len(board[0]); out=[[bg]*w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            sr,sc=r-dr,c-dc
            if 0<=sr<h and 0<=sc<w:
                out[r][c]=board[sr][sc]
    return out


def apply_cyclic_shift(board:Grid, dr:int, dc:int)->Grid:
    h,w=len(board),len(board[0])
    return [[board[(r-dr)%h][(c-dc)%w] for c in range(w)] for r in range(h)]


def infer_extra_programs(before:Grid, after:Grid, action:str)->list[dict[str,Any]]:
    out=[]
    if before==after:
        out.append({"kind":"identity_context","context":coarse_context(before)})
    local=r136.infer_local_program(before,after)
    if local is not None:
        out.append(local)
    mp=infer_mouse_patch(before,after,action)
    if mp is not None:
        out.append(mp)
    if base.same_shape(before,after) and before!=after:
        best=r167.best_nonzero_shift(before,after)
        if float(best["valid_match_fraction"])>=0.90:
            dr,dc=int(best["dr"]),int(best["dc"])
            if apply_preserve_shift(before,dr,dc)==after:
                out.append({"kind":"preserve_shift","dr":dr,"dc":dc})
            bg=base.dominant_background(before)
            if apply_bg_shift(before,dr,dc,bg)==after:
                out.append({"kind":"bg_shift","dr":dr,"dc":dc,"bg":bg})
            if apply_cyclic_shift(before,dr,dc)==after:
                out.append({"kind":"cyclic_shift","dr":dr,"dc":dc})
    return out


def infer_programs(before:Grid,after:Grid,action:str)->list[dict[str,Any]]:
    allp=[]
    allp.extend(base.infer_rules(before,after))
    allp.extend(infer_extra_programs(before,after,action))
    uniq={base.stable(p):p for p in allp}
    return [uniq[k] for k in sorted(uniq)]


def apply_program(program:dict[str,Any],board:Grid,action:str)->Grid|None:
    kind=program["kind"]
    if kind in {"identity","color_map","global_translation","component_translation"}:
        return base.apply_rule(program,board)
    if kind=="identity_context":
        return [row[:] for row in board] if coarse_context(board)==program["context"] else None
    if kind=="local_patch_rewrite":
        return r136.apply_local_program(program,board)
    if kind=="mouse_patch":
        return apply_mouse_patch(program,board,action)
    if kind=="preserve_shift":
        return apply_preserve_shift(board,int(program["dr"]),int(program["dc"]))
    if kind=="bg_shift":
        if base.dominant_background(board)!=int(program["bg"]):
            return None
        return apply_bg_shift(board,int(program["dr"]),int(program["dc"]),int(program["bg"]))
    if kind=="cyclic_shift":
        return apply_cyclic_shift(board,int(program["dr"]),int(program["dc"]))
    return None


def qualified(entry:dict[str,Any], shadow:dict[str,int], support:int, tests:int)->bool:
    return (
        entry["support"]>=support
        and len(entry["pre_states"])>=support
        and shadow["tests"]>=tests
        and shadow["wrong"]==0
    )


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    exact_outcomes:dict[str,set[str]]=defaultdict(set)
    exact_exemplar:dict[tuple[str,str],Grid]={}
    bank:dict[str,dict[str,dict[str,Any]]]=defaultdict(dict)
    shadow:dict[tuple[str,str],dict[str,int]]=defaultdict(lambda:{"tests":0,"correct":0,"wrong":0})
    stats={p:Counter() for p in POLICIES}
    mechanism_stats={p:Counter() for p in POLICIES}
    learned=Counter()
    transitions=0
    pre=events[0]

    for e in events[1:]:
        if e.get("type")!="action":
            pre=e; continue
        before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
        if not base.same_shape(before,after):
            continue
        transitions+=1
        exact_key=base.digest({"board":before,"action":action})
        pre_digest=base.digest(before)
        actual_digest=base.digest(after)
        seen=exact_outcomes.get(exact_key,set())
        exact_pred=None
        if len(seen)==1:
            d=next(iter(seen)); exact_pred=exact_exemplar[(exact_key,d)]

        akey=action_key(action)
        applicable=[]
        for pkey,entry in bank.get(akey,{}).items():
            pred=apply_program(entry["program"],before,action)
            if pred is not None:
                applicable.append((pkey,entry,pred))

        for policy,(support,tests) in POLICIES.items():
            s=stats[policy]
            s["transitions"]+=1
            candidate=exact_pred
            source="exact" if exact_pred is not None else None
            source_kinds=[]
            if candidate is None:
                preds={}
                kinds=defaultdict(set)
                for pkey,entry,pred in applicable:
                    sh=shadow[(akey,pkey)]
                    if qualified(entry,sh,support,tests):
                        dg=base.digest(pred)
                        preds[dg]=pred
                        kinds[dg].add(entry["program"]["kind"])
                if len(preds)==1:
                    dg=next(iter(preds))
                    candidate=preds[dg]
                    source="program"
                    source_kinds=sorted(kinds[dg])
                elif len(preds)>1:
                    s["conflict_abstain"]+=1
            if candidate is None:
                s["abstain"]+=1
            else:
                s["predictions"]+=1
                ok=candidate==after
                s["correct" if ok else "wrong"]+=1
                s["exact_source" if source=="exact" else "program_source"]+=1
                if source=="program":
                    for k in source_kinds:
                        mechanism_stats[policy][f"{k}:{'correct' if ok else 'wrong'}"]+=1

        # Current outcome becomes visible only now.
        for pkey,entry,pred in applicable:
            sh=shadow[(akey,pkey)]
            sh["tests"]+=1
            sh["correct" if pred==after else "wrong"]+=1

        exact_outcomes[exact_key].add(actual_digest)
        exact_exemplar[(exact_key,actual_digest)]=[row[:] for row in after]
        for program in infer_programs(before,after,action):
            pkey=base.stable(program)
            ent=bank[akey].setdefault(pkey,{"program":program,"support":0,"pre_states":set()})
            ent["support"]+=1
            ent["pre_states"].add(pre_digest)
            learned[program["kind"]]+=1

    out={"transitions":transitions,"learned_program_observations":dict(learned),"policies":{}}
    for p,s in stats.items():
        d={k:int(s[k]) for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain","exact_source","program_source")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
        d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        d["program_mechanisms"]=dict(mechanism_stats[p])
        out["policies"][p]=d
    return out


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    out={"trace_count":len(parts),"policies":{}}
    learned=Counter()
    for p in parts:
        learned.update(p.get("learned_program_observations",{}))
    out["learned_program_observations"]=dict(learned)
    for name in POLICIES:
        s=Counter()
        mech=Counter()
        for p in parts:
            d=p["policies"][name]
            for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain","exact_source","program_source"):
                s[k]+=int(d.get(k,0))
            mech.update(d.get("program_mechanisms",{}))
        d={k:int(s[k]) for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain","exact_source","program_source")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
        d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        d["program_mechanisms"]=dict(mech)
        d["strict_zero_error_program_gain"]=bool(d["program_source"]>0 and sum(v for k,v in mech.items() if k.endswith(":wrong"))==0)
        out["policies"][name]=d
    return out


def run(game:str,paths:list[Path])->dict[str,Any]:
    parts=[]
    for p in sorted(paths,key=lambda x:x.name):
        parts.append({"file":p.name,"metrics":audit_trace(base.load_events(p))})
    agg=aggregate([x["metrics"] for x in parts])
    ranked=sorted(POLICIES,key=lambda n:(
        -agg["policies"][n]["correct"],
        agg["policies"][n]["wrong"],
        -agg["policies"][n]["coverage"],
        n,
    ))
    return {
        "schema":"deus/arc3-remaining14-universal-program-ensemble/1",
        "rung":RUNG,
        "game":game,
        "trace_count":len(parts),
        "aggregate":agg,
        "ranking":ranked,
        "best_diagnostic_policy":ranked[0] if ranked else None,
        "diagnostic_gate":"UNIVERSAL_PROGRAM_PREQUENTIAL_COMPLETE",
        "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
        "truth":{
            "public_trace_only":True,
            "source_assisted_sequence_replay":True,
            "prediction_uses_preaction_and_prior_history_only":True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning":True,
            "representation_changed_from_r184":True,
            "independent_generalization_claim":False,
            "kaggle_execution":False,
            "submission_quota_spent":False,
            "owner_score_claim":False,
        },
        "per_trace":parts,
    }


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if a.game not in TARGET_GAMES:raise SystemExit("game not in remaining14")
    if not a.input:raise SystemExit("input required")
    d=run(a.game,a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"rung":RUNG,"game":a.game,"best":d["best_diagnostic_policy"],"aggregate":d["aggregate"]["policies"][d["best_diagnostic_policy"]]},sort_keys=True))
    return 0


if __name__=="__main__":raise SystemExit(main())
