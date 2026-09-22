#!/usr/bin/env python3
"""R202: ft09 phase/HUD/temporal identity-eligibility diagnostic.

Purpose: repair the concrete R193-ft09 falsifier (zero heldout coverage) without
relaxing structural-program support thresholds. This is a different
representation: predict only whether the next frame is exactly IDENTICAL to the
pre-action frame, using pre-action state/HUD/local/temporal signatures.

Protocol:
  p0..p4  fit deterministic identity gates
  p5..p9  select feature family + support using precision-first utility
  p0..p9  refit selected gate
  p10..p19 frozen heldout audit

No heldout outcome updates any mapping/selection. This diagnostic never predicts
non-identity frames and is not a Kaggle score or solver promotion by itself.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict, deque
from pathlib import Path

import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191

RUNG=202
GAME="ft09-0d8bbf25"
FAMILIES=("action","temporal","hud","local","phase_hud","phase_hud_local")
SUPPORTS=(1,2,3)
Grid=list[list[int]]


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1

def bucket(n:int)->int:
    if n<=0:return 0
    if n<=1:return 1
    if n<=2:return 2
    if n<=4:return 4
    if n<=8:return 8
    if n<=16:return 16
    if n<=32:return 32
    if n<=64:return 64
    if n<=128:return 128
    return 256

def bg(board:Grid)->int:
    return base.dominant_background(board)

def action_class(a:str)->str:
    return c191.action_class(a)

def eqmask(board:Grid,r:int,c:int)->int:
    h,w=len(board),len(board[0]);v=board[r][c];m=0
    for i,(dr,dc) in enumerate(((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1))):
        rr,cc=r+dr,c+dc
        if 0<=rr<h and 0<=cc<w and board[rr][cc]==v:m|=1<<i
    return m

def local_sig(board:Grid,a:str):
    click=c191.parse_mouse(a)
    h,w=len(board),len(board[0]);b=bg(board)
    if click is None:
        return ("no_click",)
    r,c=click
    r=max(0,min(h-1,int(r)));c=max(0,min(w-1,int(c)))
    # color-id agnostic local signature
    return ("click",r*4//max(1,h),c*4//max(1,w),int(board[r][c]==b),eqmask(board,r,c))

def hud_sig(board:Grid):
    h,w=len(board),len(board[0]);b=bg(board);cnt=Counter(v for row in board for v in row)
    nonbg=h*w-cnt[b]
    hist=tuple(sorted((bucket(n) for v,n in cnt.items() if v!=b),reverse=True)[:6])
    top=sum(v!=b for v in board[0]);bottom=sum(v!=b for v in board[-1])
    left=sum(board[r][0]!=b for r in range(h));right=sum(board[r][-1]!=b for r in range(h))
    # border occupancy and row/column activity are aimed at HUD/timer/phase cues.
    active_rows=tuple(sorted(bucket(sum(v!=b for v in row)) for row in board if any(v!=b for v in row))[:8])
    cols=[]
    for c in range(w):
        n=sum(board[r][c]!=b for r in range(h))
        if n:cols.append(bucket(n))
    active_cols=tuple(sorted(cols)[:8])
    return ("hud",h,w,len(cnt),bucket(nonbg),hist,bucket(top),bucket(bottom),bucket(left),bucket(right),active_rows,active_cols)

def temporal_sig(prev_action:str|None,run_len:int,step:int):
    return ("time",action_class(prev_action) if prev_action else "START",bucket(run_len),bucket(step))

def feature(fam:str,board:Grid,a:str,prev_action:str|None,run_len:int,step:int):
    ac=action_class(a);t=temporal_sig(prev_action,run_len,step);h=hud_sig(board);l=local_sig(board,a)
    if fam=="action":return (ac,)
    if fam=="temporal":return (ac,)+t
    if fam=="hud":return (ac,)+h
    if fam=="local":return (ac,)+l
    if fam=="phase_hud":return (ac,)+t+h
    if fam=="phase_hud_local":return (ac,)+t+h+l
    raise ValueError(fam)

def rows(paths:list[Path]):
    out=[]
    for path in sorted(paths,key=path_num):
        events=base.load_events(path);pre=events[0];prev_action=None;run_len=0;step=0
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);a=base.action_name(e);pre=e
            if not base.same_shape(before,after):
                prev_action=a;run_len=1;step+=1;continue
            ac=action_class(a)
            if prev_action is not None and action_class(prev_action)==ac:run_len+=1
            else:run_len=1
            out.append({"path":path.name,"before":before,"action":a,"prev_action":prev_action,"run_len":run_len,"step":step,"identity":before==after})
            prev_action=a;step+=1
    return out

def fit(train_rows,fam,support):
    obs=defaultdict(lambda:{"labels":Counter(),"traces":set(),"states":set()})
    for r in train_rows:
        k=feature(fam,r["before"],r["action"],r["prev_action"],r["run_len"],r["step"])
        x=obs[k];x["labels"][bool(r["identity"])]+=1;x["traces"].add(r["path"]);x["states"].add(base.digest(r["before"]))
    model={}
    for k,x in obs.items():
        # Only learn a positive identity gate when evidence is conflict-free.
        if x["labels"][True] and not x["labels"][False] and len(x["traces"])>=support and len(x["states"])>=support:
            model[k]=True
    return model

def evaluate(model,eval_rows,fam):
    s=Counter();by_action=defaultdict(Counter)
    for r in eval_rows:
        ac=action_class(r["action"]);s["transitions"]+=1;by_action[ac]["transitions"]+=1
        k=feature(fam,r["before"],r["action"],r["prev_action"],r["run_len"],r["step"])
        if k not in model:
            s["abstain"]+=1;by_action[ac]["abstain"]+=1;continue
        s["predictions"]+=1;by_action[ac]["predictions"]+=1
        ok=bool(r["identity"]);s["correct" if ok else "wrong"]+=1;by_action[ac]["correct" if ok else "wrong"]+=1
    def pack(c):
        d={k:int(c[k]) for k in ("transitions","predictions","correct","wrong","abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
        d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else 0.0
        return d
    return {"all":pack(s),"by_action":{a:pack(x) for a,x in sorted(by_action.items())}}

def run(paths:list[Path]):
    p=sorted(paths,key=path_num)
    it=[x for x in p if 0<=path_num(x)<=4];iv=[x for x in p if 5<=path_num(x)<=9];ft=[x for x in p if 0<=path_num(x)<=9];ho=[x for x in p if 10<=path_num(x)<=19]
    if tuple(map(len,(it,iv,ft,ho)))!=(5,5,10,10):raise ValueError("exact p0..p19 required")
    itr,ivr,ftr,hor=map(rows,(it,iv,ft,ho))
    configs={}
    for fam in FAMILIES:
        for sup in SUPPORTS:
            model=fit(itr,fam,sup);val=evaluate(model,ivr,fam)["all"]
            configs[f"{fam}|s{sup}"]={"family":fam,"support":sup,"model_keys":len(model),"validation":val}
    def ckey(item):
        name,cfg=item;d=cfg["validation"]
        # False identity predictions are very costly. Then maximize correct coverage.
        utility=d["correct"]-10*d["wrong"]
        return (-utility,d["wrong"],-d["correct"],-(d["coverage"] or 0),name)
    sel_name,sel=sorted(configs.items(),key=ckey)[0]
    frozen=fit(ftr,sel["family"],sel["support"]);held=evaluate(frozen,hor,sel["family"])
    return {
      "schema":"deus/arc3-ft09-phase-hud-identity-gate/1","rung":RUNG,"game":GAME,
      "protocol":{"inner_train":"p0-p4","inner_validation":"p5-p9","refit":"p0-p9","heldout":"p10-p19","heldout_learning":False},
      "inner":{"configs":configs,"selected":sel_name,"selected_family":sel["family"],"selected_support":sel["support"]},
      "heldout":held,
      "diagnostic_gate":"FT09_PHASE_HUD_IDENTITY_GATE_HELDOUT_COMPLETE",
      "promotion":{"solver_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"same_game_public_heldout":True,"pre_action_features_only":True,"inner_selection_only_p0_p9":True,"heldout_never_updates_selector":True,"predicts_identity_only":True,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"rung":RUNG,"selected":d["inner"]["selected"],"heldout":d["heldout"]["all"]},sort_keys=True))
if __name__=="__main__":main()
