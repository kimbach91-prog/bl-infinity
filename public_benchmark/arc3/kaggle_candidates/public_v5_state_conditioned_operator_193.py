#!/usr/bin/env python3
"""R193: state-conditioned action-relative operator search for remaining14.

R188: 14/14 formerly uncovered families are local-patch-rich.
R190/R191 show that unconditioned patch transfer creates many false exact
predictions. R193 adds pre-action state context instead of relaxing gates.

Candidate context families are selected only on p5..p9 after fitting p0..p4,
then refit on p0..p9 and frozen for p10..p19:
  base           structural patch only
  board          + coarse board phase signature
  local          + action-local 3x3 equality signature
  component      + clicked/center component morphology
  board_local    + board + local
  board_component+ board + component

MOUSE programs are click-relative. Directional programs are rotated so the
action points RIGHT before learning/applying. Current heldout outcomes never
update programs, contexts, family choice, support or voting policy.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_remaining14_structural_patch_heldout_191 as s191
import public_v5_canonical_patch_router_191 as c191

RUNG=193
TARGET_GAMES=c191.TARGET_GAMES
FAMILIES=("base","board","local","component","board_local","board_component")
POLICIES={
    "strict3":{"support":3,"vote":False},
    "strict2":{"support":2,"vote":False},
    "vote2":{"support":2,"vote":True,"share":0.65,"margin":1.75},
    "vote1":{"support":1,"vote":True,"share":0.85,"margin":2.5},
}
DIRS=c191.DIRS
Grid=list[list[int]]


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name);return int(m.group(1)) if m else -1


def bucket(n:int)->int:
    if n<=0:return 0
    if n<=1:return 1
    if n<=2:return 2
    if n<=4:return 4
    if n<=8:return 8
    if n<=16:return 16
    if n<=32:return 32
    if n<=64:return 64
    return 128


def bg(board:Grid)->int:return base.dominant_background(board)


def board_ctx(board:Grid):
    h,w=len(board),len(board[0]);b=bg(board);cnt=Counter(v for row in board for v in row)
    nonbg=h*w-cnt[b]
    # Coarse histogram is color-id agnostic except background share.
    freq=sorted((n for v,n in cnt.items() if v!=b),reverse=True)
    return ("board",h,w,len(cnt),bucket(nonbg),tuple(bucket(x) for x in freq[:6]))


def eqsig(board:Grid,r:int,c:int)->int:
    h,w=len(board),len(board[0]);v=board[r][c];out=0;bit=0
    for dr,dc in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
        rr,cc=r+dr,c+dc
        if 0<=rr<h and 0<=cc<w and board[rr][cc]==v:out|=1<<bit
        bit+=1
    return out


def component_desc(board:Grid,r0:int,c0:int):
    h,w=len(board),len(board[0]);v=board[r0][c0];q=deque([(r0,c0)]);seen={(r0,c0)};cells=[];rmin=rmax=r0;cmin=cmax=c0
    while q:
        r,c=q.popleft();cells.append((r,c));rmin=min(rmin,r);rmax=max(rmax,r);cmin=min(cmin,c);cmax=max(cmax,c)
        for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
            rr,cc=r+dr,c+dc
            if 0<=rr<h and 0<=cc<w and (rr,cc) not in seen and board[rr][cc]==v:
                seen.add((rr,cc));q.append((rr,cc))
        if len(cells)>256:break
    touch=int(any(r in (0,h-1) or c in (0,w-1) for r,c in cells))
    return ("comp",bucket(len(cells)),bucket(rmax-rmin+1),bucket(cmax-cmin+1),touch)


def anchor_for(board:Grid,action:str,program)->tuple[int,int]:
    click=c191.parse_mouse(action)
    if click is not None:return click
    # Directional/nonmouse: use the patch center as anchor when program stores its training bbox.
    rr=int(program.get("anchor_r",len(board)//2));cc=int(program.get("anchor_c",len(board[0])//2))
    return max(0,min(len(board)-1,rr)),max(0,min(len(board[0])-1,cc))


def ctx_for(family:str,board:Grid,action:str,program):
    r,c=anchor_for(board,action,program)
    local=("local",eqsig(board,r,c),int(board[r][c]==bg(board)),r*4//max(1,len(board)),c*4//max(1,len(board[0])))
    comp=component_desc(board,r,c)
    b=board_ctx(board)
    if family=="base":return ("base",)
    if family=="board":return b
    if family=="local":return local
    if family=="component":return comp
    if family=="board_local":return b+local
    if family=="board_component":return b+comp
    raise ValueError(family)


def infer_program(before:Grid,after:Grid,action:str,pad:int):
    if action in DIRS:
        nb=c191.transform_board(before,action,True);na=c191.transform_board(after,action,True)
        p=s191.infer_struct(nb,na,"RIGHT",pad,False)
        if p is None:return None
        p=dict(p);p["normalized_dir"]=True;p["action_key"]="DIR"
        # diff center in normalized board for context anchor
        box=s191.diff_box(nb,na)
        if box is not None:p["anchor_r"]=(box[0]+box[2])//2;p["anchor_c"]=(box[1]+box[3])//2
        return p
    click=c191.parse_mouse(action)
    if click is not None:
        p=s191.infer_struct(before,after,action,pad,True)
        if p is None:return None
        p=dict(p);p["normalized_dir"]=False;p["action_key"]="MOUSE";p["anchor_r"]=click[0];p["anchor_c"]=click[1]
        return p
    p=s191.infer_struct(before,after,action,pad,False)
    if p is None:return None
    p=dict(p);p["normalized_dir"]=False;p["action_key"]=c191.action_class(action)
    box=s191.diff_box(before,after)
    if box is not None:p["anchor_r"]=(box[0]+box[2])//2;p["anchor_c"]=(box[1]+box[3])//2
    return p


def action_key(action:str)->str:
    if action in DIRS:return "DIR"
    if c191.parse_mouse(action) is not None:return "MOUSE"
    return c191.action_class(action)


def apply_program(program,board:Grid,action:str,index_cache):
    if program.get("normalized_dir"):
        nb=c191.transform_board(board,action,True)
        pred=s191.apply_program(program,nb,"RIGHT",index_cache)
        return c191.inverse_board(pred,action,True) if pred is not None else None
    return s191.apply_program(program,board,action,index_cache)


def train(paths:list[Path],family:str):
    bank=defaultdict(dict);meta=Counter()
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            for pad in (0,1):
                p=infer_program(before,after,action,pad)
                if p is None:continue
                keyctx=ctx_for(family,c191.transform_board(before,action,True) if p.get("normalized_dir") else before, "RIGHT" if p.get("normalized_dir") else action,p)
                key=base.stable({"p":p,"ctx":keyctx});akey=p["action_key"];sd=base.digest(before)
                ent=bank[akey].setdefault(key,{"program":p,"ctx":keyctx,"obs":0,"traces":set(),"states":set()})
                ent["obs"]+=1;ent["traces"].add(path.name);ent["states"].add(sd);meta[p["kind"]]+=1
    return bank,dict(meta)


def choose(policy,bank,before,action,family):
    cfg=POLICIES[policy];akey=action_key(action);rows=[];struct_cache={}
    for ent in bank.get(akey,{}).values():
        if len(ent["traces"])<cfg["support"] or len(ent["states"])<cfg["support"]:continue
        p=ent["program"]
        ctx_board=c191.transform_board(before,action,True) if p.get("normalized_dir") else before
        ctx_action="RIGHT" if p.get("normalized_dir") else action
        if ctx_for(family,ctx_board,ctx_action,p)!=ent["ctx"]:continue
        pred=apply_program(p,before,action,struct_cache)
        if pred is not None:rows.append((base.digest(pred),pred,len(ent["traces"]),p["kind"]))
    if not rows:return None,False
    groups={}
    for dg,pred,wt,kind in rows:
        g=groups.setdefault(dg,{"pred":pred,"weight":0});g["weight"]+=wt
    if not cfg["vote"]:
        if len(groups)!=1:return None,True
        return next(iter(groups.values()))["pred"],False
    ranked=sorted(groups.items(),key=lambda kv:(-kv[1]["weight"],kv[0]));top=ranked[0][1];total=sum(v["weight"] for _,v in ranked);second=ranked[1][1]["weight"] if len(ranked)>1 else 0
    share=top["weight"]/total;margin=top["weight"]/second if second else 999
    if share<cfg["share"] or margin<cfg["margin"]:return None,len(groups)>1
    return top["pred"],len(groups)>1


def evaluate(bank,paths,family,policy):
    s=Counter();by_action=defaultdict(Counter)
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            ac=c191.action_class(action);s["transitions"]+=1;by_action[ac]["transitions"]+=1
            pred,conf=choose(policy,bank,before,action,family)
            if pred is None:
                s["abstain"]+=1;by_action[ac]["abstain"]+=1;s["conflict_abstain"]+=int(conf);by_action[ac]["conflict_abstain"]+=int(conf)
            else:
                s["predictions"]+=1;by_action[ac]["predictions"]+=1;ok=pred==after;s["correct" if ok else "wrong"]+=1;by_action[ac]["correct" if ok else "wrong"]+=1
    def pack(c):
        d={k:int(c[k]) for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None;d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        return d
    return {"all":pack(s),"by_action":{a:pack(x) for a,x in sorted(by_action.items())}}


def run(game,paths):
    it=sorted([p for p in paths if 0<=path_num(p)<=4],key=path_num);iv=sorted([p for p in paths if 5<=path_num(p)<=9],key=path_num);ft=sorted([p for p in paths if 0<=path_num(p)<=9],key=path_num);ho=sorted([p for p in paths if 10<=path_num(p)<=19],key=path_num)
    if tuple(map(len,(it,iv,ft,ho)))!=(5,5,10,10):raise ValueError("need p0..p19")

    inner={}
    for fam in FAMILIES:
        bank,_=train(it,fam)
        for pol in POLICIES:
            inner[f"{fam}|{pol}"]=evaluate(bank,iv,fam,pol)
    actions=sorted({a for x in inner.values() for a in x["by_action"]})
    selection={}
    for ac in actions:
        def key(name):
            d=inner[name]["by_action"].get(ac,{"correct":0,"wrong":0,"coverage":0});u=d["correct"]-3*d["wrong"]
            return (-u,-d["correct"],d["wrong"],-(d["coverage"] or 0),name)
        selection[ac]=sorted(inner,key=key)

    # Choose fallback depth on validation only.
    # Re-evaluate by trying ranked family|policy candidates per action.
    full_banks={}
    for fam in FAMILIES:full_banks[fam]=train(ft,fam)[0]

    def routed(paths,banks,depth):
        s=Counter();chosen=Counter()
        for path in paths:
            events=base.load_events(path);pre=events[0]
            for e in events[1:]:
                if e.get("type")!="action":pre=e;continue
                before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
                if not base.same_shape(before,after):continue
                ac=c191.action_class(action);s["transitions"]+=1;pred=None;used=None
                for name in selection.get(ac,list(inner))[:depth]:
                    fam,pol=name.split("|",1);pred,_=choose(pol,banks[fam],before,action,fam)
                    if pred is not None:used=name;break
                if pred is None:s["abstain"]+=1
                else:
                    chosen[used]+=1;s["predictions"]+=1;s["correct" if pred==after else "wrong"]+=1
        d={k:int(s[k]) for k in ("transitions","predictions","correct","wrong","abstain")};d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None;d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        return {"all":d,"chosen":dict(chosen)}

    # Depth selection requires inner-train banks, not full train.
    inner_banks={fam:train(it,fam)[0] for fam in FAMILIES}
    depth_stats={str(d):routed(iv,inner_banks,d) for d in (1,2,3,4)}
    def dkey(d):
        x=depth_stats[str(d)]["all"];u=x["correct"]-3*x["wrong"];return (-u,-x["correct"],x["wrong"],-(x["coverage"] or 0),d)
    depth=sorted((1,2,3,4),key=dkey)[0]
    held=routed(ho,full_banks,depth)

    return {"schema":"deus/arc3-v5-state-conditioned-operator/1","rung":RUNG,"game":game,"protocol":{"inner_train":"p0-p4","inner_validation":"p5-p9","refit":"p0-p9","heldout":"p10-p19"},"inner":{"selection":{a:v[:4] for a,v in selection.items()},"depth_stats":depth_stats,"selected_depth":depth},"heldout":held,"diagnostic_gate":"STATE_CONDITIONED_OPERATOR_HELDOUT_COMPLETE","promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},"truth":{"public_trace_only":True,"pre_action_context_only":True,"inner_selection_uses_only_p0_p9":True,"heldout_p10_p19_never_updates_programs_or_router":True,"kaggle_execution":False,"submission_quota_spent":False}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if a.game not in TARGET_GAMES:raise SystemExit("game not target")
    d=run(a.game,a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps({"rung":RUNG,"game":a.game,"depth":d["inner"]["selected_depth"],"selection":d["inner"]["selection"],"heldout":d["heldout"]["all"]},sort_keys=True))

if __name__=="__main__":main()
