#!/usr/bin/env python3
"""R194: action-agnostic viewport-shift solver for remaining14, targeting su15.

R188 exposed the key missed mechanism in su15:
  MOUSE transitions, yet 73%+ of all transitions have >=0.98 dense shift fit,
  dominated by horizontal shift (0,-1).

R180 had hard-coded camera handling to UP/DOWN. R194 removes that assumption.
It learns stable dense viewport shifts per action class from training outcomes,
then predicts future full boards from pre-action state only.

Nested protocol:
  p0..p4 train candidate shift models
  p5..p9 select render + confidence per action class
  p0..p9 refit
  p10..p19 frozen heldout

Render candidates:
  preserve: incoming boundary preserves current cells
  background: incoming boundary filled with current dominant background
  cyclic: toroidal shift

Heldout outcomes never update shifts, render choice or confidence thresholds.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_dense_scroll_renderer_audit_167 as r167
import public_v5_canonical_patch_router_191 as c191

RUNG=194
TARGET_GAMES=c191.TARGET_GAMES
RENDERS=("preserve","background","cyclic")
THRESHOLDS=(0.50,0.70,0.85,0.95)
MIN_SUPPORTS=(1,2,3)
Grid=list[list[int]]


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name);return int(m.group(1)) if m else -1


def action_key(action:str)->str:
    if c191.parse_mouse(action) is not None:return "MOUSE"
    return c191.action_class(action)


def shift_preserve(board:Grid,dr:int,dc:int)->Grid:
    h,w=len(board),len(board[0]);out=[row[:] for row in board]
    for r in range(h):
        for c in range(w):
            sr,sc=r-dr,c-dc
            if 0<=sr<h and 0<=sc<w:out[r][c]=board[sr][sc]
    return out


def shift_background(board:Grid,dr:int,dc:int)->Grid:
    h,w=len(board),len(board[0]);b=base.dominant_background(board);out=[[b]*w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            sr,sc=r-dr,c-dc
            if 0<=sr<h and 0<=sc<w:out[r][c]=board[sr][sc]
    return out


def shift_cyclic(board:Grid,dr:int,dc:int)->Grid:
    h,w=len(board),len(board[0])
    return [[board[(r-dr)%h][(c-dc)%w] for c in range(w)] for r in range(h)]


def render(board:Grid,shift,kind:str)->Grid:
    dr,dc=shift
    if kind=="preserve":return shift_preserve(board,dr,dc)
    if kind=="background":return shift_background(board,dr,dc)
    if kind=="cyclic":return shift_cyclic(board,dr,dc)
    raise ValueError(kind)


def train(paths:list[Path]):
    bank=defaultdict(Counter);meta=Counter()
    for p in paths:
        events=base.load_events(p);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            changed=sum(before[r][c]!=after[r][c] for r in range(len(before)) for c in range(len(before[0])))
            if not changed:continue
            b=r167.best_nonzero_shift(before,after);fit=float(b["valid_match_fraction"])
            meta["transitions_changed"]+=1
            if fit>=0.98:
                sh=(int(b["dr"]),int(b["dc"]));bank[action_key(action)][sh]+=1;meta["fit098"]+=1
    return bank,dict(meta)


def stable(bank,action,threshold,min_support):
    c=bank.get(action,Counter())
    if not c:return None,0.0,0
    sh,n=c.most_common(1)[0];total=sum(c.values());share=n/total if total else 0
    return (sh if n>=min_support and share>=threshold else None),share,n


def evaluate_config(bank,paths,render_kind,threshold,min_support):
    s=Counter();by_action=defaultdict(Counter);chosen={}
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            ak=action_key(action);s["transitions"]+=1;by_action[ak]["transitions"]+=1
            sh,share,support=stable(bank,ak,threshold,min_support)
            if sh is None:
                s["abstain"]+=1;by_action[ak]["abstain"]+=1;continue
            pred=render(before,sh,render_kind);s["predictions"]+=1;by_action[ak]["predictions"]+=1
            ok=pred==after;s["correct" if ok else "wrong"]+=1;by_action[ak]["correct" if ok else "wrong"]+=1
            chosen[ak]={"shift":list(sh),"share":round(share,6),"support":support}
    def pack(c):
        d={k:int(c[k]) for k in ("transitions","predictions","correct","wrong","abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None;d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        return d
    return {"all":pack(s),"by_action":{a:pack(x) for a,x in sorted(by_action.items())},"chosen":chosen}


def run(game,paths):
    it=sorted([p for p in paths if 0<=path_num(p)<=4],key=path_num);iv=sorted([p for p in paths if 5<=path_num(p)<=9],key=path_num);ft=sorted([p for p in paths if 0<=path_num(p)<=9],key=path_num);ho=sorted([p for p in paths if 10<=path_num(p)<=19],key=path_num)
    if tuple(map(len,(it,iv,ft,ho)))!=(5,5,10,10):raise ValueError("need p0..p19")
    ibank,imeta=train(it)
    configs={}
    for rk in RENDERS:
        for th in THRESHOLDS:
            for ms in MIN_SUPPORTS:
                name=f"{rk}|t{th}|s{ms}"
                configs[name]={"render":rk,"threshold":th,"min_support":ms,"validation":evaluate_config(ibank,iv,rk,th,ms)}
    def key(name):
        d=configs[name]["validation"]["all"];u=d["correct"]-3*d["wrong"]
        return (-u,-d["correct"],d["wrong"],-(d["coverage"] or 0),name)
    selected_name=sorted(configs,key=key)[0];sel=configs[selected_name]
    fbank,fmeta=train(ft)
    held=evaluate_config(fbank,ho,sel["render"],sel["threshold"],sel["min_support"])
    return {"schema":"deus/arc3-generalized-viewport-shift-heldout/1","rung":RUNG,"game":game,"protocol":{"inner_train":"p0-p4","inner_validation":"p5-p9","refit":"p0-p9","heldout":"p10-p19"},"inner":{"train_meta":imeta,"selected":selected_name,"selected_config":{k:sel[k] for k in ("render","threshold","min_support")},"validation":sel["validation"]["all"]},"refit_meta":fmeta,"heldout":held,"diagnostic_gate":"GENERALIZED_VIEWPORT_HELDOUT_COMPLETE","promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},"truth":{"public_trace_only":True,"action_agnostic_shift_learning":True,"inner_selection_uses_only_p0_p9":True,"heldout_p10_p19_never_updates_shift_or_renderer":True,"kaggle_execution":False,"submission_quota_spent":False}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if a.game not in TARGET_GAMES:raise SystemExit("game not target")
    d=run(a.game,a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps({"rung":RUNG,"game":a.game,"selected":d["inner"]["selected"],"refit_meta":d["refit_meta"],"heldout":d["heldout"]["all"],"chosen":d["heldout"]["chosen"]},sort_keys=True))

if __name__=="__main__":main()
