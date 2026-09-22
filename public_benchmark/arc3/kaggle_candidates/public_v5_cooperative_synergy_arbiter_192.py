#!/usr/bin/env python3
"""R192: V5 cooperative-synergy arbiter over three independent remaining14 lanes.

Independent cores:
  U = R190 universal executable-program transfer
  S = R191 structural/color-canonical patch transfer
  C = R191 V5 canonical/action-relative patch families

The arbiter is chosen without heldout leakage:
  p0..p4  fit all candidate lanes
  p5..p9  score/rank lane variants PER action class and select fallback depth
  p0..p9  refit frozen lanes
  p10..p19 heldout execution with the frozen router

This instantiates the V5 COOPERATIVE_SYNERGY / INDEPENDENT_DUAL pattern:
independent hypothesis families first, then a validation-grounded arbiter.
No heldout outcome updates any lane, ranking, or fallback policy.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_remaining14_heldout_program_transfer_190 as u190
import public_remaining14_structural_patch_heldout_191 as s191
import public_v5_canonical_patch_router_191 as c191

RUNG=192
TARGET_GAMES=u190.TARGET_GAMES
U_POLICIES=("strict3","strict2","vote2","vote1")
S_POLICIES=("strict3","strict2","vote2","vote1")
C_FAMILIES=c191.FAMILIES
CANDIDATES=tuple([f"U:{p}" for p in U_POLICIES]+[f"S:{p}" for p in S_POLICIES]+[f"C:{f}" for f in C_FAMILIES])


def path_num(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1


def action_class(action:str)->str:
    return c191.action_class(action)


def build_lanes(paths:list[Path]):
    ubank,_=u190.train_bank(paths)
    sbank,_=s191.train(paths)
    cbanks=c191.fit(paths,C_FAMILIES)
    return {"U":ubank,"S":sbank,"C":cbanks}


def predict(candidate:str,lanes,before,action,struct_index_cache):
    typ,name=candidate.split(":",1)
    if typ=="U":
        return u190.candidate_for(name,lanes["U"],before,action)[0]
    if typ=="S":
        return s191.choose(name,lanes["S"],before,action,struct_index_cache)[0]
    if typ=="C":
        return c191.apply_family(name,lanes["C"][name],before,action)[0]
    raise ValueError(candidate)


def evaluate_candidates(lanes,paths:list[Path]):
    by_candidate={c:defaultdict(Counter) for c in CANDIDATES}
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            ac=action_class(action);struct_cache={}
            for cand in CANDIDATES:
                s=by_candidate[cand][ac];s["transitions"]+=1
                pred=predict(cand,lanes,before,action,struct_cache)
                if pred is None:
                    s["abstain"]+=1
                else:
                    s["predictions"]+=1
                    s["correct" if pred==after else "wrong"]+=1
    def pack(c):
        d={k:int(c[k]) for k in ("transitions","predictions","correct","wrong","abstain")}
        d["accuracy"]=round(d["correct"]/d["predictions"],6) if d["predictions"] else None
        d["coverage"]=round(d["predictions"]/d["transitions"],6) if d["transitions"] else None
        return d
    return {cand:{ac:pack(s) for ac,s in sorted(rows.items())} for cand,rows in by_candidate.items()}


def rank_for_action(stats,action,penalty:int):
    def key(cand):
        d=stats[cand].get(action,{"correct":0,"wrong":0,"coverage":0})
        utility=int(d.get("correct",0))-penalty*int(d.get("wrong",0))
        return (-utility,-int(d.get("correct",0)),int(d.get("wrong",0)),-float(d.get("coverage") or 0),cand)
    return sorted(CANDIDATES,key=key)


def route_eval(lanes,paths,ranking,depth:int):
    s=Counter();by_action=defaultdict(Counter);chosen=Counter()
    for path in paths:
        events=base.load_events(path);pre=events[0]
        for e in events[1:]:
            if e.get("type")!="action":pre=e;continue
            before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
            if not base.same_shape(before,after):continue
            ac=action_class(action);s["transitions"]+=1;by_action[ac]["transitions"]+=1;struct_cache={}
            pred=None;used=None
            for cand in ranking.get(ac,list(CANDIDATES))[:depth]:
                pred=predict(cand,lanes,before,action,struct_cache)
                if pred is not None:
                    used=cand;break
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
    return {"all":pack(s),"by_action":{a:pack(x) for a,x in sorted(by_action.items())},"chosen":dict(chosen)}


def run(game:str,paths:list[Path]):
    inner_train=sorted([p for p in paths if 0<=path_num(p)<=4],key=path_num)
    inner_val=sorted([p for p in paths if 5<=path_num(p)<=9],key=path_num)
    full_train=sorted([p for p in paths if 0<=path_num(p)<=9],key=path_num)
    heldout=sorted([p for p in paths if 10<=path_num(p)<=19],key=path_num)
    if tuple(map(len,(inner_train,inner_val,full_train,heldout)))!=(5,5,10,10):
        raise ValueError("exact p0..p19 split required")

    inner_lanes=build_lanes(inner_train)
    stats=evaluate_candidates(inner_lanes,inner_val)
    actions=sorted({a for cand in stats.values() for a in cand})
    configs={}
    for penalty in (1,2,3):
        ranking={a:rank_for_action(stats,a,penalty) for a in actions}
        for depth in (1,2,3,4):
            key=f"p{penalty}_d{depth}"
            configs[key]={
                "penalty":penalty,"depth":depth,
                "ranking":ranking,
                "validation":route_eval(inner_lanes,inner_val,ranking,depth),
            }

    def ckey(item):
        name,cfg=item;d=cfg["validation"]["all"]
        # First maximize correctness adjusted by false predictions, then raw correct/coverage.
        utility=d["correct"]-2*d["wrong"]
        return (-utility,-d["correct"],d["wrong"],-(d["coverage"] or 0),name)
    selected_name,selected=sorted(configs.items(),key=ckey)[0]

    full_lanes=build_lanes(full_train)
    held=route_eval(full_lanes,heldout,selected["ranking"],selected["depth"])

    return {
      "schema":"deus/arc3-v5-cooperative-synergy-arbiter/1","rung":RUNG,"game":game,
      "cores":["R190_UNIVERSAL_PROGRAM","R191_STRUCTURAL_PATCH","R191_CANONICAL_ACTION_RELATIVE"],
      "protocol":{"inner_train":"p0-p4","inner_validation":"p5-p9","refit":"p0-p9","heldout":"p10-p19","heldout_learning":False},
      "inner":{"candidate_stats":stats,"config_summaries":{k:{"penalty":v["penalty"],"depth":v["depth"],"validation":v["validation"]["all"]} for k,v in configs.items()},"selected_config":selected_name,"selected_penalty":selected["penalty"],"selected_depth":selected["depth"],"top3_per_action":{a:r[:3] for a,r in selected["ranking"].items()}},
      "heldout":held,
      "diagnostic_gate":"V5_COOPERATIVE_SYNERGY_HELDOUT_COMPLETE",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"same_game_public_heldout":True,"independent_core_generation":True,"arbiter_selected_on_inner_validation_only":True,"heldout_p10_p19_never_updates_cores_or_arbiter":True,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False},
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if a.game not in TARGET_GAMES:raise SystemExit("game not target")
    d=run(a.game,a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"rung":RUNG,"game":a.game,"selected":d["inner"]["selected_config"],"top3":d["inner"]["top3_per_action"],"heldout":d["heldout"]["all"]},sort_keys=True))

if __name__=="__main__":main()
