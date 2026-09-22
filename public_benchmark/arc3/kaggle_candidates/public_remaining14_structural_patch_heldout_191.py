#!/usr/bin/env python3
"""R191: color-canonical structural local-patch transfer for remaining14.

R188 proved all14 previously uncovered public families are local-patch-rich.
R190 literal local-patch transfer still overfits color/value details in several
families. R191 removes literal color identity from the precondition whenever
possible.

A patch is represented by:
  * row-major equality pattern of pre-patch colors (canonical token ids),
  * post-patch cells expressed as references to pre tokens when possible,
    otherwise explicit constants,
  * optional click-relative offset for MOUSE actions.

Programs are learned only from p0..p9 and frozen before p10..p19 evaluation.
Heldout outcomes never update the model.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_remaining14_universal_program_ensemble_189 as r189

RUNG=191
TARGET_GAMES=r189.TARGET_GAMES
POLICIES={
    "strict3":{"min_trace_support":3,"vote":False},
    "strict2":{"min_trace_support":2,"vote":False},
    "vote2":{"min_trace_support":2,"vote":True,"min_share":0.60,"min_margin":1.5},
    "vote1":{"min_trace_support":1,"vote":True,"min_share":0.80,"min_margin":2.0},
}
Grid=list[list[int]]


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name);return int(m.group(1)) if m else -1


def canon(patch:Grid):
    mp={}; vals=[]; pat=[]
    for row in patch:
        rr=[]
        for v in row:
            if v not in mp:
                mp[v]=len(vals);vals.append(v)
            rr.append(mp[v])
        pat.append(rr)
    return pat,vals


def encode_post(post:Grid,pre_vals:list[int]):
    rev={v:i for i,v in enumerate(pre_vals)}
    return [[["R",rev[v]] if v in rev else ["C",int(v)] for v in row] for row in post]


def instantiate(roles,vals):
    out=[]
    for row in roles:
        rr=[]
        for kind,x in row:
            rr.append(vals[int(x)] if kind=="R" else int(x))
        out.append(rr)
    return out


def diff_box(before:Grid,after:Grid):
    h,w=len(before),len(before[0]);pts=[(r,c) for r in range(h) for c in range(w) if before[r][c]!=after[r][c]]
    if not pts:return None
    return min(r for r,_ in pts),min(c for _,c in pts),max(r for r,_ in pts),max(c for _,c in pts)


def extract(g:Grid,r0,c0,r1,c1):return [row[c0:c1+1] for row in g[r0:r1+1]]


def infer_struct(before:Grid,after:Grid,action:str,pad:int,mouse:bool):
    if not base.same_shape(before,after) or before==after:return None
    box=diff_box(before,after)
    if box is None:return None
    h,w=len(before),len(before[0]);r0,c0,r1,c1=box
    r0=max(0,r0-pad);c0=max(0,c0-pad);r1=min(h-1,r1+pad);c1=min(w-1,c1+pad)
    if r0==0 and c0==0 and r1==h-1 and c1==w-1:return None
    pre=extract(before,r0,c0,r1,c1);post=extract(after,r0,c0,r1,c1)
    pat,vals=canon(pre)
    p={"kind":"mouse_struct_patch" if mouse else "struct_patch","h":len(pre),"w":len(pre[0]),"pre_pattern":pat,"post_roles":encode_post(post,vals),"pad":pad}
    if mouse:
        click=r189.parse_mouse(action)
        if click is None:return None
        p["dr"]=r0-click[0];p["dc"]=c0-click[1]
    return p


def infer_programs(before,after,action):
    out=[]
    for pad in (0,1):
        p=infer_struct(before,after,action,pad,False)
        if p is not None:out.append(p)
        if r189.parse_mouse(action) is not None:
            q=infer_struct(before,after,action,pad,True)
            if q is not None:out.append(q)
    uniq={base.stable(x):x for x in out}
    return [uniq[k] for k in sorted(uniq)]


def window(g,r0,c0,h,w):return [row[c0:c0+w] for row in g[r0:r0+h]]


def match_at(program,board,r0,c0):
    h,w=int(program["h"]),int(program["w"])
    if r0<0 or c0<0 or r0+h>len(board) or c0+w>len(board[0]):return None
    p=window(board,r0,c0,h,w);pat,vals=canon(p)
    if pat!=program["pre_pattern"]:return None
    post=instantiate(program["post_roles"],vals)
    out=[row[:] for row in board]
    for rr in range(h):out[r0+rr][c0:c0+w]=post[rr][:]
    return out


def apply_program(program,board,action):
    kind=program["kind"];h,w=int(program["h"]),int(program["w"])
    if kind=="mouse_struct_patch":
        click=r189.parse_mouse(action)
        if click is None:return None
        return match_at(program,board,click[0]+int(program["dr"]),click[1]+int(program["dc"]))
    if kind=="struct_patch":
        hits=[]
        for r0 in range(len(board)-h+1):
            for c0 in range(len(board[0])-w+1):
                p=window(board,r0,c0,h,w);pat,_=canon(p)
                if pat==program["pre_pattern"]:hits.append((r0,c0))
                if len(hits)>1:return None
        if len(hits)!=1:return None
        return match_at(program,board,*hits[0])
    return None


def train(paths):
    bank=defaultdict(dict);meta=Counter()
    for p in paths:
        trace=p.name;events=base.load_events(p);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            meta["transitions"]+=1;akey=r189.action_key(action);pd=base.digest(before)
            for prog in infer_programs(before,after,action):
                key=base.stable(prog);ent=bank[akey].setdefault(key,{"program":prog,"obs":0,"traces":set(),"pre_states":set()})
                ent["obs"]+=1;ent["traces"].add(trace);ent["pre_states"].add(pd);meta[prog["kind"]]+=1
    return bank,dict(meta)


def choose(policy,bank,before,action):
    cfg=POLICIES[policy];rows=[]
    for ent in bank.get(r189.action_key(action),{}).values():
        ts=len(ent["traces"])
        if ts<cfg["min_trace_support"]:continue
        pred=apply_program(ent["program"],before,action)
        if pred is not None:rows.append((base.digest(pred),pred,ts,ent["program"]["kind"]))
    if not rows:return None,{"conflict":False,"kinds":[]}
    groups={}
    for dg,pred,wt,kind in rows:
        g=groups.setdefault(dg,{"pred":pred,"weight":0,"kinds":set()});g["weight"]+=wt;g["kinds"].add(kind)
    if not cfg.get("vote"):
        if len(groups)!=1:return None,{"conflict":True,"kinds":sorted({k for *_,k in rows})}
        g=next(iter(groups.values()));return g["pred"],{"conflict":False,"kinds":sorted(g["kinds"])}
    ranked=sorted(groups.items(),key=lambda kv:(-kv[1]["weight"],kv[0]));top=ranked[0][1];total=sum(v["weight"] for _,v in ranked)
    share=top["weight"]/total;second=ranked[1][1]["weight"] if len(ranked)>1 else 0;margin=top["weight"]/second if second else 999
    if share<cfg["min_share"] or margin<cfg["min_margin"]:return None,{"conflict":len(groups)>1,"kinds":sorted({k for *_,k in rows})}
    return top["pred"],{"conflict":len(groups)>1,"kinds":sorted(top["kinds"])}


def evaluate(bank,paths):
    stats={p:Counter() for p in POLICIES};mech={p:Counter() for p in POLICIES}
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            for p in POLICIES:
                s=stats[p];s["transitions"]+=1;pred,info=choose(p,bank,before,action)
                if pred is None:
                    s["abstain"]+=1;s["conflict_abstain"]+=int(info.get("conflict",False));continue
                s["predictions"]+=1;ok=pred==after;s["correct" if ok else "wrong"]+=1
                for k in info.get("kinds",[]):mech[p][f"{k}:{'correct' if ok else 'wrong'}"]+=1
    out={}
    for p,s in stats.items():
        d={k:int(s[k]) for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None;d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None;d["mechanisms"]=dict(mech[p]);out[p]=d
    return out


def run(game,paths):
    trainp=sorted([p for p in paths if 0<=path_num(p)<=9],key=path_num);testp=sorted([p for p in paths if 10<=path_num(p)<=19],key=path_num)
    if len(trainp)!=10 or len(testp)!=10:raise ValueError("need p0..p19")
    bank,meta=train(trainp);pol=evaluate(bank,testp);ranked=sorted(POLICIES,key=lambda n:(-pol[n]["correct"],pol[n]["wrong"],-pol[n]["coverage"],n))
    return {"schema":"deus/arc3-remaining14-structural-patch-heldout/1","rung":RUNG,"game":game,"train":{"programs":sum(len(v) for v in bank.values()),"meta":meta},"heldout":{"policies":pol,"ranking":ranked,"best_diagnostic_policy":ranked[0]},"diagnostic_gate":"STRUCTURAL_PATCH_HELDOUT_COMPLETE","promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},"truth":{"public_trace_only":True,"train_only_p0_p9":True,"heldout_p10_p19_never_updates_model":True,"color_canonical_patch_representation":True,"independent_hidden_game_generalization_claim":False,"kaggle_execution":False,"submission_quota_spent":False}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if a.game not in TARGET_GAMES:raise SystemExit("game not target")
    d=run(a.game,a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8");b=d["heldout"]["best_diagnostic_policy"];print(json.dumps({"rung":RUNG,"game":a.game,"best":b,"stats":d["heldout"]["policies"][b],"programs":d["train"]["programs"]},sort_keys=True))

if __name__=="__main__":main()
