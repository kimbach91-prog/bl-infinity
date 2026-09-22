#!/usr/bin/env python3
"""R191: V5-routed canonical local-program solver for R184's remaining 14 families.

Goal
----
R188 proved all 14 formerly zero-opportunity families are local-patch-rich.
R189 then produced at least one exact prequential prediction in all 14, but
literal local rewrites still overfit. R191 changes representation again.

V5 pattern used here:
  GENERATE -> EVALUATE -> ARCHIVE -> ROUTE -> HELDOUT VERIFY

Candidate families:
  * literal local patch (R136 baseline)
  * color-isomorphic local patch, padding 0/1/2
  * direction-normalized color-isomorphic patch (UP/DOWN/LEFT/RIGHT -> RIGHT)
  * click-relative color-isomorphic patch for MOUSE actions

Selection is nested and leak-resistant:
  p0..p4  = inner-train
  p5..p9  = inner-validation; selects one family PER action class
  p0..p9  = refit selected families
  p10..p19 = frozen heldout; no learning or retuning

No p10..p19 outcome influences representation, family choice, program support,
or routing. Public same-game heldout only, not hidden-game generalization.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import public_executable_world_model_134 as base
import public_local_transition_program_prequential_136 as r136

RUNG = 191
TARGET_GAMES = (
    "bp35-0a0ad940","ft09-0d8bbf25","g50t-5849a774","lf52-271a04aa",
    "lp85-305b61c3","ls20-9607627b","m0r0-492f87ba","r11l-495a7899",
    "s5i5-18d95033","sb26-7fbdac44","su15-1944f8ab","tn36-ef4dde99",
    "tr87-cd924810","vc33-5430563c",
)
DIRS={"UP","DOWN","LEFT","RIGHT"}
FAMILIES=("literal_p1","iso_p0","iso_p1","iso_p2","dir_iso_p0","dir_iso_p1","mouse_iso_p0","mouse_iso_p1")
MIN_TRACE_SUPPORT=2
MIN_STATE_SUPPORT=2
Grid=list[list[int]]


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1


def action_class(action:str)->str:
    if action.startswith("MOUSE("): return "MOUSE"
    if action in DIRS: return "DIR"
    return action or "UNKNOWN"


def rotate_cw(g:Grid)->Grid:
    return [list(row) for row in zip(*g[::-1])]


def rotate(g:Grid,k:int)->Grid:
    out=[row[:] for row in g]
    for _ in range(k%4): out=rotate_cw(out)
    return out


def norm_rotation(action:str)->int|None:
    # Rotate observed board clockwise until directional action points RIGHT.
    return {"RIGHT":0,"UP":1,"LEFT":2,"DOWN":3}.get(action)


def transform_board(g:Grid, action:str, normalized:bool)->Grid:
    k=norm_rotation(action) if normalized else 0
    if k is None: return [row[:] for row in g]
    return rotate(g,k)


def inverse_board(g:Grid, action:str, normalized:bool)->Grid:
    k=norm_rotation(action) if normalized else 0
    if k is None: return [row[:] for row in g]
    return rotate(g,(-k)%4)


def parse_mouse(action:str)->tuple[int,int]|None:
    m=re.match(r"MOUSE\(row=(-?\d+),\s*col=(-?\d+)\)",action)
    return (int(m.group(1)),int(m.group(2))) if m else None


def canonical_patch(patch:Grid,bg:int)->tuple[str,list[int]]:
    """Canonicalize colors with global background role0 then first occurrence."""
    role={bg:0}; rev=[bg]
    out=[]
    for row in patch:
        rr=[]
        for v in row:
            if v not in role:
                role[v]=len(rev);rev.append(v)
            rr.append(role[v])
        out.append(rr)
    return base.stable(out),rev


def output_template(after_patch:Grid,roles:list[int])->list[list[list[Any]]]:
    pos={v:i for i,v in enumerate(roles)}
    out=[]
    for row in after_patch:
        rr=[]
        for v in row:
            rr.append(["R",pos[v]] if v in pos else ["L",int(v)])
        out.append(rr)
    return out


def realize_template(tmpl,roles:list[int])->Grid|None:
    out=[]
    for row in tmpl:
        rr=[]
        for typ,val in row:
            if typ=="R":
                if not (0<=int(val)<len(roles)): return None
                rr.append(int(roles[int(val)]))
            else:
                rr.append(int(val))
        out.append(rr)
    return out


def diff_box(before:Grid,after:Grid,pad:int)->tuple[int,int,int,int]|None:
    if not base.same_shape(before,after) or before==after:return None
    h,w=len(before),len(before[0])
    pts=[(r,c) for r in range(h) for c in range(w) if before[r][c]!=after[r][c]]
    if not pts:return None
    r0=max(0,min(r for r,_ in pts)-pad);r1=min(h-1,max(r for r,_ in pts)+pad)
    c0=max(0,min(c for _,c in pts)-pad);c1=min(w-1,max(c for _,c in pts)+pad)
    if r0==0 and c0==0 and r1==h-1 and c1==w-1:return None
    return r0,c0,r1,c1


def sub(g:Grid,b):
    r0,c0,r1,c1=b
    return [row[c0:c1+1] for row in g[r0:r1+1]]


@dataclass
class Program:
    kind:str
    action_key:str
    h:int
    w:int
    before_sig:str
    after_template:list[list[list[Any]]]
    dr:int|None=None
    dc:int|None=None


class Bank:
    def __init__(self):
        # action -> kind -> (h,w,before_sig,dr,dc,after_template_stable) -> metadata
        self.rows=defaultdict(dict)
        self.sizes=defaultdict(lambda:defaultdict(set))

    def add(self,p:Program,trace:str,state_digest:str):
        key=base.stable({
            "h":p.h,"w":p.w,"before":p.before_sig,
            "dr":p.dr,"dc":p.dc,"after":p.after_template,
        })
        d=self.rows[(p.action_key,p.kind)].setdefault(key,{
            "program":p,"obs":0,"traces":set(),"states":set(),
        })
        d["obs"]+=1;d["traces"].add(trace);d["states"].add(state_digest)
        self.sizes[(p.action_key,p.kind)].add((p.h,p.w))

    def eligible(self,action_key:str,kind:str):
        for d in self.rows.get((action_key,kind),{}).values():
            if len(d["traces"])>=MIN_TRACE_SUPPORT and len(d["states"])>=MIN_STATE_SUPPORT:
                yield d


def infer_iso(before:Grid,after:Grid,action:str,pad:int,normalized:bool,kind:str)->Program|None:
    b0=transform_board(before,action,normalized)
    a0=transform_board(after,action,normalized)
    box=diff_box(b0,a0,pad)
    if box is None:return None
    pre=sub(b0,box);post=sub(a0,box);bg=base.dominant_background(b0)
    sig,roles=canonical_patch(pre,bg)
    r0,c0,r1,c1=box
    return Program(kind, "DIR" if normalized else action_class(action), len(pre),len(pre[0]),sig,output_template(post,roles))


def infer_mouse_iso(before:Grid,after:Grid,action:str,pad:int,kind:str)->Program|None:
    click=parse_mouse(action)
    if click is None:return None
    box=diff_box(before,after,pad)
    if box is None:return None
    pre=sub(before,box);post=sub(after,box);bg=base.dominant_background(before)
    sig,roles=canonical_patch(pre,bg)
    r0,c0,_,_=box
    return Program(kind,"MOUSE",len(pre),len(pre[0]),sig,output_template(post,roles),r0-click[0],c0-click[1])


def infer_literal(before:Grid,after:Grid,action:str)->Program|None:
    p=r136.infer_local_program(before,after)
    if p is None:return None
    pre=base.as_grid(p["before_patch"]);post=base.as_grid(p["after_patch"])
    # Literal encoded as direct template. before_sig stores literal patch stable.
    tmpl=[[["L",int(v)] for v in row] for row in post]
    return Program("literal_p1",action_class(action),len(pre),len(pre[0]),base.stable(pre),tmpl)


def infer_family(family:str,before:Grid,after:Grid,action:str)->Program|None:
    if family=="literal_p1":return infer_literal(before,after,action)
    if family.startswith("iso_p"):
        return infer_iso(before,after,action,int(family[-1]),False,family)
    if family.startswith("dir_iso_p"):
        if action not in DIRS:return None
        return infer_iso(before,after,action,int(family[-1]),True,family)
    if family.startswith("mouse_iso_p"):
        return infer_mouse_iso(before,after,action,int(family[-1]),family)
    raise ValueError(family)


def fit(paths:list[Path],families:Iterable[str])->dict[str,Bank]:
    banks={f:Bank() for f in families}
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            sd=base.digest(before)
            for f in families:
                p=infer_family(f,before,after,action)
                if p is not None:banks[f].add(p,path.name,sd)
    return banks


def apply_at(board:Grid,r0:int,c0:int,p:Program,roles:list[int])->Grid|None:
    post=realize_template(p.after_template,roles)
    if post is None:return None
    h,w=len(board),len(board[0])
    if r0<0 or c0<0 or r0+p.h>h or c0+p.w>w:return None
    out=[row[:] for row in board]
    for rr in range(p.h):out[r0+rr][c0:c0+p.w]=post[rr][:]
    return out


def apply_family(family:str,bank:Bank,before:Grid,action:str)->tuple[Grid|None,dict[str,Any]]:
    normalized=family.startswith("dir_iso_")
    b0=transform_board(before,action,normalized)
    akey="DIR" if normalized else action_class(action)
    if family.startswith("mouse_iso_"):
        akey="MOUSE"
    groups=defaultdict(lambda:{"weight":0,"pred":None,"kinds":set()})
    applicable=0

    if family=="literal_p1":
        # Scan all literal patch sizes once, exact lookup by window bytes.
        for ph,pw in bank.sizes.get((akey,family),set()):
            for r0 in range(len(b0)-ph+1):
                for c0 in range(len(b0[0])-pw+1):
                    patch=[row[c0:c0+pw] for row in b0[r0:r0+ph]]
                    sig=base.stable(patch)
                    for d in bank.eligible(akey,family):
                        p=d["program"]
                        if p.h!=ph or p.w!=pw or p.before_sig!=sig:continue
                        pred=apply_at(b0,r0,c0,p,[])
                        if pred is None:continue
                        applicable+=1;dg=base.digest(pred);g=groups[dg]
                        g["weight"]+=len(d["traces"]);g["pred"]=pred;g["kinds"].add(family)
    elif family.startswith("mouse_iso_"):
        click=parse_mouse(action)
        if click is None:return None,{"applicable":0,"conflict":False}
        bg=base.dominant_background(b0)
        for d in bank.eligible("MOUSE",family):
            p=d["program"];r0=click[0]+int(p.dr or 0);c0=click[1]+int(p.dc or 0)
            if r0<0 or c0<0 or r0+p.h>len(b0) or c0+p.w>len(b0[0]):continue
            patch=[row[c0:c0+p.w] for row in b0[r0:r0+p.h]]
            sig,roles=canonical_patch(patch,bg)
            if sig!=p.before_sig:continue
            pred=apply_at(b0,r0,c0,p,roles)
            if pred is None:continue
            applicable+=1;dg=base.digest(pred);g=groups[dg]
            g["weight"]+=len(d["traces"]);g["pred"]=pred;g["kinds"].add(family)
    else:
        bg=base.dominant_background(b0)
        # Index eligible programs by (h,w,before_sig) to avoid program x window loops.
        idx=defaultdict(list)
        for d in bank.eligible(akey,family):
            p=d["program"];idx[(p.h,p.w,p.before_sig)].append(d)
        sizes=sorted({(h,w) for h,w,_ in idx})
        for ph,pw in sizes:
            for r0 in range(len(b0)-ph+1):
                for c0 in range(len(b0[0])-pw+1):
                    patch=[row[c0:c0+pw] for row in b0[r0:r0+ph]]
                    sig,roles=canonical_patch(patch,bg)
                    for d in idx.get((ph,pw,sig),[]):
                        p=d["program"];pred=apply_at(b0,r0,c0,p,roles)
                        if pred is None:continue
                        applicable+=1;dg=base.digest(pred);g=groups[dg]
                        g["weight"]+=len(d["traces"]);g["pred"]=pred;g["kinds"].add(family)

    if not groups:return None,{"applicable":applicable,"conflict":False}
    ranked=sorted(groups.items(),key=lambda kv:(-kv[1]["weight"],kv[0]))
    if len(ranked)>1 and ranked[0][1]["weight"]<=ranked[1][1]["weight"]:
        return None,{"applicable":applicable,"conflict":True,"top_weight":ranked[0][1]["weight"],"second_weight":ranked[1][1]["weight"]}
    pred=ranked[0][1]["pred"]
    if normalized:pred=inverse_board(pred,action,True)
    return pred,{"applicable":applicable,"conflict":len(groups)>1,"top_weight":ranked[0][1]["weight"]}


def evaluate_family(family:str,bank:Bank,paths:list[Path])->dict[str,Any]:
    s=Counter();by_action=defaultdict(Counter)
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            ac=action_class(action);s["transitions"]+=1;by_action[ac]["transitions"]+=1
            pred,info=apply_family(family,bank,before,action)
            if pred is None:
                s["abstain"]+=1;by_action[ac]["abstain"]+=1
                if info.get("conflict"):s["conflict_abstain"]+=1;by_action[ac]["conflict_abstain"]+=1
            else:
                s["predictions"]+=1;by_action[ac]["predictions"]+=1
                ok=pred==after
                s["correct" if ok else "wrong"]+=1;by_action[ac]["correct" if ok else "wrong"]+=1
    def pack(c):
        d={k:int(c[k]) for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
        d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        return d
    return {"all":pack(s),"by_action":{a:pack(c) for a,c in sorted(by_action.items())}}


def family_rank(stats:dict[str,Any],action:str)->list[str]:
    def score(f):
        d=stats[f]["by_action"].get(action,{"correct":0,"wrong":0,"coverage":0})
        # Penalize false exact predictions harder than abstention.
        utility=int(d.get("correct",0))-2*int(d.get("wrong",0))
        return (-utility,-int(d.get("correct",0)),int(d.get("wrong",0)),-float(d.get("coverage") or 0),f)
    return sorted(FAMILIES,key=score)


def evaluate_routed(selection:dict[str,list[str]],banks:dict[str,Bank],paths:list[Path],fallback_depth:int)->dict[str,Any]:
    s=Counter();by_action=defaultdict(Counter);chosen=Counter()
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            ac=action_class(action);s["transitions"]+=1;by_action[ac]["transitions"]+=1
            pred=None;used=None
            for fam in selection.get(ac,list(FAMILIES))[:fallback_depth]:
                pred,_=apply_family(fam,banks[fam],before,action)
                if pred is not None:
                    used=fam;break
            if pred is None:
                s["abstain"]+=1;by_action[ac]["abstain"]+=1
            else:
                chosen[used]+=1;s["predictions"]+=1;by_action[ac]["predictions"]+=1
                ok=pred==after
                s["correct" if ok else "wrong"]+=1;by_action[ac]["correct" if ok else "wrong"]+=1
    def pack(c):
        d={k:int(c[k]) for k in ("transitions","predictions","correct","wrong","abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
        d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        return d
    return {"all":pack(s),"by_action":{a:pack(c) for a,c in sorted(by_action.items())},"chosen_family_counts":dict(chosen)}


def run(game:str,paths:list[Path])->dict[str,Any]:
    inner_train=sorted([p for p in paths if 0<=path_num(p)<=4],key=path_num)
    inner_val=sorted([p for p in paths if 5<=path_num(p)<=9],key=path_num)
    full_train=sorted([p for p in paths if 0<=path_num(p)<=9],key=path_num)
    heldout=sorted([p for p in paths if 10<=path_num(p)<=19],key=path_num)
    if tuple(map(len,(inner_train,inner_val,full_train,heldout)))!=(5,5,10,10):
        raise ValueError("need exact p0..p19 split")

    inner_banks=fit(inner_train,FAMILIES)
    inner_stats={f:evaluate_family(f,inner_banks[f],inner_val) for f in FAMILIES}
    action_classes=sorted({a for f in FAMILIES for a in inner_stats[f]["by_action"]})
    selection={a:family_rank(inner_stats,a) for a in action_classes}

    # Select fallback depth from inner validation only.
    inner_routed={}
    for depth in (1,2,3):
        inner_routed[str(depth)]=evaluate_routed(selection,inner_banks,inner_val,depth)
    def dscore(depth):
        d=inner_routed[str(depth)]["all"]
        return (-(d["correct"]-2*d["wrong"]),-d["correct"],d["wrong"],-(d["coverage"] or 0),depth)
    selected_depth=sorted((1,2,3),key=dscore)[0]

    full_banks=fit(full_train,FAMILIES)
    held=evaluate_routed(selection,full_banks,heldout,selected_depth)

    return {
      "schema":"deus/arc3-v5-canonical-patch-router/1",
      "rung":RUNG,
      "game":game,
      "protocol":{
        "inner_train":"p0-p4","inner_validation":"p5-p9",
        "refit":"p0-p9","heldout":"p10-p19",
        "heldout_learning":False,
        "selection_per_action_class":True,
      },
      "inner":{
        "family_stats":inner_stats,
        "selection":selection,
        "fallback_depth_stats":inner_routed,
        "selected_fallback_depth":selected_depth,
      },
      "heldout":held,
      "diagnostic_gate":"V5_CANONICAL_PATCH_HELDOUT_COMPLETE",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{
        "public_trace_only":True,
        "same_game_public_heldout":True,
        "representation_changed_from_r189":True,
        "inner_selection_uses_only_p0_p9":True,
        "heldout_p10_p19_never_updates_model_or_router":True,
        "generate_evaluate_archive_route_pattern":True,
        "kaggle_execution":False,
        "submission_quota_spent":False,
        "owner_score_claim":False,
      },
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if a.game not in TARGET_GAMES:raise SystemExit("game not in remaining14")
    d=run(a.game,a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"rung":RUNG,"game":a.game,"depth":d["inner"]["selected_fallback_depth"],"selection":{k:v[:3] for k,v in d["inner"]["selection"].items()},"heldout":d["heldout"]["all"]},sort_keys=True))

if __name__=="__main__":main()
