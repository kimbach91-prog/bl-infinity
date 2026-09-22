#!/usr/bin/env python3
"""R195: generalized viewport + residual patch composition, targeted at SU15.

R190 literal cross-trajectory transfer abstained completely on heldout SU15,
while R188 shows SU15 is both local-patch rich and uniquely dense-shift rich.
R194 generalizes the viewport shift beyond arrow actions. R195 composes that
global motion with a frozen click-relative structural residual learned from
training only.

Nested protocol:
  p0..p4  learn shift + residual candidates
  p5..p9  select render / support / conflict fallback
  p0..p9  refit frozen model
  p10..p19 frozen heldout

Heldout outcomes never update shifts, residuals, or selection.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
import public_remaining14_structural_patch_heldout_191 as s191
import public_generalized_viewport_shift_194 as r194

RUNG=195
GAME="su15-1944f8ab"
RENDERS=("preserve","background","cyclic")
SUPPORTS=(1,2,3)
CONFLICT=("abstain","base")
PADS=(0,1)


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1


def shift_model(paths):
    bank,_=r194.train(paths)
    out={}
    for ak,c in bank.items():
        if c:
            sh,n=c.most_common(1)[0]; total=sum(c.values())
            out[ak]={"shift":sh,"share":n/total if total else 0.0,"support":n,"total":total}
    return out


def shift_for(model,action,share_min=0.50,support_min=2):
    ak=r194.action_key(action);d=model.get(ak)
    if not d or d["share"]<share_min or d["support"]<support_min:return None
    return d["shift"]


def residual_program(base_pred,after,action,pad):
    mouse=c191.parse_mouse(action) is not None
    return s191.infer_struct(base_pred,after,action,pad,mouse)


def train_residual(paths,render_kind):
    sm=shift_model(paths)
    bank=defaultdict(dict); meta=Counter()
    for path in paths:
        events=base.load_events(path); pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            sh=shift_for(sm,action)
            if sh is None:continue
            bp=r194.render(before,sh,render_kind)
            meta["shifted"]+=1
            if bp==after:
                meta["base_exact"]+=1
                continue
            for pad in PADS:
                p=residual_program(bp,after,action,pad)
                if p is None:continue
                key=base.stable(p);ak=r194.action_key(action);sd=base.digest(bp)
                ent=bank[ak].setdefault(key,{"program":p,"obs":0,"traces":set(),"states":set()})
                ent["obs"]+=1;ent["traces"].add(path.name);ent["states"].add(sd)
                meta[f"program_p{pad}"]+=1
    return sm,bank,dict(meta)


def residual_predict(bank,base_pred,action,support):
    rows=[];cache={}
    for ent in bank.get(r194.action_key(action),{}).values():
        if len(ent["traces"])<support or len(ent["states"])<support:continue
        pred=s191.apply_program(ent["program"],base_pred,action,cache)
        if pred is not None:rows.append((base.digest(pred),pred,len(ent["traces"])))
    if not rows:return None,False
    groups={}
    for dg,pred,wt in rows:
        g=groups.setdefault(dg,{"pred":pred,"weight":0});g["weight"]+=wt
    ranked=sorted(groups.items(),key=lambda kv:(-kv[1]["weight"],kv[0]))
    if len(ranked)>1 and ranked[0][1]["weight"]<=ranked[1][1]["weight"]:
        return None,True
    return ranked[0][1]["pred"],len(groups)>1


def evaluate(sm,bank,paths,render_kind,support,conflict):
    s=Counter();by_action=defaultdict(Counter)
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            s["transitions"]+=1
            sh=shift_for(sm,action)
            if sh is None:
                s["abstain"]+=1;continue
            bp=r194.render(before,sh,render_kind)
            rp,had_conflict=residual_predict(bank,bp,action,support)
            if rp is not None:
                pred=rp;s["residual_source"]+=1
            elif had_conflict and conflict=="abstain":
                s["abstain"]+=1;s["conflict_abstain"]+=1;continue
            else:
                pred=bp;s["base_source"]+=1
            s["predictions"]+=1
            s["correct" if pred==after else "wrong"]+=1
    d={k:int(s[k]) for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain","base_source","residual_source")}
    d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
    d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
    return d


def run(paths):
    it=sorted([p for p in paths if 0<=path_num(p)<=4],key=path_num)
    iv=sorted([p for p in paths if 5<=path_num(p)<=9],key=path_num)
    ft=sorted([p for p in paths if 0<=path_num(p)<=9],key=path_num)
    ho=sorted([p for p in paths if 10<=path_num(p)<=19],key=path_num)
    if tuple(map(len,(it,iv,ft,ho)))!=(5,5,10,10):raise ValueError("need p0..p19")
    trained={rk:train_residual(it,rk) for rk in RENDERS}
    configs={}
    for rk in RENDERS:
        sm,bank,meta=trained[rk]
        for support in SUPPORTS:
            for conflict in CONFLICT:
                name=f"{rk}|s{support}|{conflict}"
                configs[name]={"render":rk,"support":support,"conflict":conflict,"train_meta":meta,"validation":evaluate(sm,bank,iv,rk,support,conflict)}
    def key(name):
        d=configs[name]["validation"];u=d["correct"]-4*d["wrong"]
        return (-u,-d["correct"],d["wrong"],-(d["coverage"] or 0),name)
    selected_name=sorted(configs,key=key)[0];sel=configs[selected_name]
    sm,bank,meta=train_residual(ft,sel["render"])
    held=evaluate(sm,bank,ho,sel["render"],sel["support"],sel["conflict"])
    return {
      "schema":"deus/arc3-su15-shift-residual-heldout/1","rung":RUNG,"game":GAME,
      "inner":{"selected":selected_name,"selected_config":{k:sel[k] for k in ("render","support","conflict")},"validation":sel["validation"],"train_meta":sel["train_meta"]},
      "refit":{"shift_model":{k:{**v,"shift":list(v["shift"])} for k,v in sm.items()},"meta":meta,"residual_programs":sum(len(v) for v in bank.values())},
      "heldout":held,
      "diagnostic_gate":"SU15_SHIFT_RESIDUAL_HELDOUT_COMPLETE",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"same_game_public_heldout":True,"inner_selection_uses_only_p0_p9":True,"heldout_p10_p19_never_updates_shift_residual_or_selection":True,"kaggle_execution":False,"submission_quota_spent":False},
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"rung":RUNG,"selected":d["inner"]["selected"],"validation":d["inner"]["validation"],"refit":d["refit"],"heldout":d["heldout"]},sort_keys=True))
if __name__=="__main__":main()
