#!/usr/bin/env python3
"""R190: frozen train10 -> heldout10 program transfer for R184's remaining14.

R189 measures same-trace prequential program learning. R190 tests a stronger
question without using heldout outcomes for learning: can reusable executable
programs learned from public trajectories p0..p9 predict exact full boards on
p10..p19 of the SAME public game family?

Training stores only executable programs from R189 (identity-context, R134
rules, local patch, click-relative patch, viewport/cyclic shifts) with support
counts across distinct training traces and distinct pre-states.

Heldout evaluation is fully frozen. No p10..p19 outcome updates any program,
support, reliability or selection threshold.

This is public same-game heldout evidence, not hidden-game generalization and
not a Kaggle score.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_remaining14_universal_program_ensemble_189 as r189

RUNG=190
TARGET_GAMES=r189.TARGET_GAMES
POLICIES={
    "strict3": {"min_trace_support":3,"vote":False},
    "strict2": {"min_trace_support":2,"vote":False},
    "vote2": {"min_trace_support":2,"vote":True,"min_share":0.60,"min_margin":2.0},
    "vote1": {"min_trace_support":1,"vote":True,"min_share":0.80,"min_margin":3.0},
}


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1


def train_bank(paths:list[Path]):
    bank=defaultdict(dict)
    learned=Counter()
    transitions=0
    for p in paths:
        trace=p.name
        events=base.load_events(p)
        pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":
                pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            transitions+=1
            akey=r189.action_key(action);pd=base.digest(before)
            for program in r189.infer_programs(before,after,action):
                pkey=base.stable(program)
                ent=bank[akey].setdefault(pkey,{"program":program,"obs":0,"traces":set(),"pre_states":set()})
                ent["obs"]+=1;ent["traces"].add(trace);ent["pre_states"].add(pd)
                learned[program["kind"]]+=1
    return bank,{"transitions":transitions,"program_observations":dict(learned)}


def candidate_for(policy:str,bank,before,action):
    cfg=POLICIES[policy]; akey=r189.action_key(action)
    rows=[]
    for pkey,ent in bank.get(akey,{}).items():
        ts=len(ent["traces"])
        if ts<cfg["min_trace_support"]:continue
        pred=r189.apply_program(ent["program"],before,action)
        if pred is None:continue
        rows.append((base.digest(pred),pred,ts,ent["obs"],ent["program"]["kind"]))
    if not rows:return None,{"applicable":0,"conflict":False,"kinds":[]}
    grouped={}
    for dg,pred,ts,obs,kind in rows:
        g=grouped.setdefault(dg,{"pred":pred,"weight":0,"trace_weight":0,"kinds":set(),"programs":0})
        g["weight"]+=ts
        g["trace_weight"]+=ts
        g["kinds"].add(kind);g["programs"]+=1
    if not cfg.get("vote"):
        if len(grouped)!=1:
            return None,{"applicable":len(rows),"conflict":True,"kinds":sorted({k for *_,k in rows})}
        g=next(iter(grouped.values()))
        return g["pred"],{"applicable":len(rows),"conflict":False,"kinds":sorted(g["kinds"])}
    ranked=sorted(grouped.items(),key=lambda kv:(-kv[1]["weight"],kv[0]))
    top=ranked[0][1]; total=sum(x["weight"] for _,x in ranked)
    share=top["weight"]/total if total else 0
    second=ranked[1][1]["weight"] if len(ranked)>1 else 0
    margin=(top["weight"]/second) if second else 999.0
    if share<cfg["min_share"] or margin<cfg["min_margin"]:
        return None,{"applicable":len(rows),"conflict":len(grouped)>1,"share":round(share,4),"margin":round(margin,4),"kinds":sorted({k for *_,k in rows})}
    return top["pred"],{"applicable":len(rows),"conflict":len(grouped)>1,"share":round(share,4),"margin":round(margin,4),"kinds":sorted(top["kinds"])}


def evaluate(bank,paths:list[Path]):
    stats={p:Counter() for p in POLICIES}
    mech={p:Counter() for p in POLICIES}
    per_trace=[]
    for path in paths:
        local={p:Counter() for p in POLICIES}
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            for p in POLICIES:
                s=stats[p];ls=local[p]
                s["transitions"]+=1;ls["transitions"]+=1
                pred,info=candidate_for(p,bank,before,action)
                if pred is None:
                    s["abstain"]+=1;ls["abstain"]+=1
                    if info.get("conflict"):s["conflict_abstain"]+=1;ls["conflict_abstain"]+=1
                    continue
                s["predictions"]+=1;ls["predictions"]+=1
                ok=pred==after
                s["correct" if ok else "wrong"]+=1;ls["correct" if ok else "wrong"]+=1
                for k in info.get("kinds",[]):mech[p][f"{k}:{'correct' if ok else 'wrong'}"]+=1
        per_trace.append({"file":path.name,"policies":{p:dict(x) for p,x in local.items()}})
    out={}
    for p,s in stats.items():
        d={k:int(s[k]) for k in ("transitions","predictions","correct","wrong","abstain","conflict_abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
        d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        d["mechanisms"]=dict(mech[p])
        out[p]=d
    return out,per_trace


def run(game:str,paths:list[Path]):
    train=sorted([p for p in paths if 0<=path_num(p)<=9],key=path_num)
    test=sorted([p for p in paths if 10<=path_num(p)<=19],key=path_num)
    if len(train)!=10 or len(test)!=10:
        raise ValueError(f"need p0..p19 exactly; train={len(train)} test={len(test)}")
    bank,train_meta=train_bank(train)
    frozen_programs=sum(len(v) for v in bank.values())
    policies,per_trace=evaluate(bank,test)
    ranked=sorted(POLICIES,key=lambda n:(-policies[n]["correct"],policies[n]["wrong"],-policies[n]["coverage"],n))
    return {
      "schema":"deus/arc3-remaining14-heldout-program-transfer/1","rung":RUNG,"game":game,
      "protocol":{"train_paths":[f"p{i}" for i in range(10)],"heldout_paths":[f"p{i}" for i in range(10,20)],"heldout_learning":False},
      "train":{"meta":train_meta,"frozen_programs":frozen_programs,"action_keys":sorted(bank)},
      "heldout":{"policies":policies,"ranking":ranked,"best_diagnostic_policy":ranked[0] if ranked else None,"per_trace":per_trace},
      "diagnostic_gate":"FROZEN_SAME_GAME_HELDOUT_PROGRAM_TRANSFER_COMPLETE",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"same_game_public_heldout":True,"train_only_p0_p9":True,"heldout_p10_p19_never_updates_model":True,"independent_hidden_game_generalization_claim":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False},
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if a.game not in TARGET_GAMES:raise SystemExit("game not in remaining14")
    d=run(a.game,a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    b=d["heldout"]["best_diagnostic_policy"];print(json.dumps({"rung":RUNG,"game":a.game,"best":b,"stats":d["heldout"]["policies"][b],"frozen_programs":d["train"]["frozen_programs"]},sort_keys=True))

if __name__=="__main__":main()
