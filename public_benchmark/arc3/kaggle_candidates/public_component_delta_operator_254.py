#!/usr/bin/env python3
"""R254: source-free component-anchored relative delta operator for g50t.

Grounding: R253 found no whole-frame shifts, but g50t has repeated normalized
transition delta shapes (roughly 0.30-0.46 top-signature reuse on several
movement/action classes), unlike re86. R254 therefore represents a transition
as edits relative to a visible connected-component anchor rather than as an
absolute next frame.

Protocol per game:
  p0-p4   fit candidate component-delta rules
  p5-p9   choose per-action variant only when it makes >0 added full-frame
          predictions and ZERO validation errors
  p0-p9   refit selected variants
  p10-p19 frozen public-development evaluation
Exact visible-state/action lookup retains precedence.

This reads public traces only; no game source, hidden data, Kaggle runtime,
leaderboard result, or upstream score is used.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251

RUNG=254
MIN_SUPPORT=2
VARIANTS=(
    ("color_shape",0),("color_shape",2),("color_shape",5),
    ("shape",0),("shape",2),("shape",5),
)


def components(board:list[list[int]])->list[dict[str,Any]]:
    b=r246.bg(board); h=len(board); w=len(board[0]); seen=set(); out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen or int(board[r][c])==b: continue
            color=int(board[r][c]); q=deque([(r,c)]); seen.add((r,c)); pts=[]
            while q:
                rr,cc=q.popleft(); pts.append((rr,cc))
                for nr,nc in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and int(board[nr][nc])==color:
                        seen.add((nr,nc)); q.append((nr,nc))
            r0=min(x for x,y in pts); c0=min(y for x,y in pts)
            r1=max(x for x,y in pts); c1=max(y for x,y in pts)
            shape=tuple(sorted((x-r0,y-c0) for x,y in pts))
            out.append({"color":color,"r0":r0,"c0":c0,"r1":r1,"c1":c1,"shape":shape,"area":len(pts)})
    return out


def comp_sig(comp:dict[str,Any], mode:str)->str:
    if mode=="color_shape": x=(comp["color"],comp["shape"])
    elif mode=="shape": x=comp["shape"]
    else: raise KeyError(mode)
    return r246.stable(x)


def changed_patch(before,after):
    h=len(before); w=len(before[0]); ch=[]
    for r in range(h):
        for c in range(w):
            bv=int(before[r][c]); av=int(after[r][c])
            if bv!=av: ch.append((r,c,bv,av))
    if not ch: return None
    r0=min(x[0] for x in ch); c0=min(x[1] for x in ch)
    r1=max(x[0] for x in ch); c1=max(x[1] for x in ch)
    return {"r0":r0,"c0":c0,"r1":r1,"c1":c1,"changes":ch}


def near(comp,patch,radius:int)->bool:
    return not (
        comp["r1"] < patch["r0"]-radius or comp["r0"] > patch["r1"]+radius or
        comp["c1"] < patch["c0"]-radius or comp["c0"] > patch["c1"]+radius
    )


def spec_for(comp,patch):
    # Store edits relative to anchor top-left, including expected old value.
    return (
        patch["r0"]-comp["r0"], patch["c0"]-comp["c0"],
        tuple(sorted((r-patch["r0"],c-patch["c0"],bv,av) for r,c,bv,av in patch["changes"]))
    )


def fit_rules(rows, mode:str, radius:int):
    obs=defaultdict(Counter); supports=defaultdict(set)
    for row in rows:
        patch=changed_patch(row["before"],row["after"])
        if patch is None: continue
        for comp in components(row["before"]):
            if not near(comp,patch,radius): continue
            key=r246.stable((row["action"],comp_sig(comp,mode)))
            spec=spec_for(comp,patch)
            obs[key][r246.stable(spec)]+=1
            supports[(key,r246.stable(spec))].add(row["transition_id"])
    rules={}
    for key,c in obs.items():
        if len(c)!=1: continue
        ss=next(iter(c))
        if len(supports[(key,ss)])<MIN_SUPPORT: continue
        rules[key]=json.loads(ss)
    return rules


def apply_spec(board,comp,spec):
    off_r,off_c,changes=spec
    pr0=comp["r0"]+int(off_r); pc0=comp["c0"]+int(off_c)
    h=len(board); w=len(board[0]); out=[list(map(int,row)) for row in board]
    for dr,dc,old,new in changes:
        r=pr0+int(dr); c=pc0+int(dc)
        if not (0<=r<h and 0<=c<w): return None
        if int(board[r][c])!=int(old): return None
        out[r][c]=int(new)
    return out


def predict(row,rules,mode):
    preds={}
    for comp in components(row["before"]):
        key=r246.stable((row["action"],comp_sig(comp,mode)))
        spec=rules.get(key)
        if spec is None: continue
        p=apply_spec(row["before"],comp,spec)
        if p is not None: preds[r246.digest(p)]=p
    if len(preds)!=1: return None
    return next(iter(preds.values()))


def prepare(paths):
    out=[]
    for p in paths:
        rows=r251.prepare_rows([p])
        for step,row in enumerate(rows):
            x=dict(row); x["transition_id"]=f"{p.name}#{step}"; out.append(x)
    return out


def eval_rows(rows, exact, rules, mode):
    s=Counter(); examples=[]
    for row in rows:
        s["transitions"]+=1
        if row["exact_key"] in exact:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        p=predict(row,rules,mode)
        if p is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        ok=(p==row["after"])
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        if len(examples)<20: examples.append({"trace":row["trace"],"action":row["action"],"correct":ok})
    n=s["candidate_predictions"]; opp=s["baseline_abstain"]
    return {**dict(s),"accuracy":round(s["candidate_correct"]/n,6) if n else None,
            "coverage_of_baseline_abstain":round(n/opp,6) if opp else 0.0,"examples":examples}


def evaluate_game(paths):
    ps=sorted(paths,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise ValueError(f"exact p0..p19 required, got {nums}")
    parts=[prepare([p]) for p in ps]
    tr=[r for x in parts[:5] for r in x]; va=[r for x in parts[5:10] for r in x]
    fit=[r for x in parts[:10] for r in x]; ho=[r for x in parts[10:] for r in x]
    exact_tr=r251.fit_exact(tr)
    tr_by=defaultdict(list); va_by=defaultdict(list); fit_by=defaultdict(list)
    for r in tr: tr_by[r["action"]].append(r)
    for r in va: va_by[r["action"]].append(r)
    for r in fit: fit_by[r["action"]].append(r)
    selected={}; diag={}
    for action in sorted(set(tr_by)|set(va_by)):
        cand={}
        for mode,radius in VARIANTS:
            rules=fit_rules(tr_by[action],mode,radius)
            met=eval_rows(va_by[action],exact_tr,rules,mode)
            key=f"{mode}_r{radius}"
            cand[key]={"rule_count":len(rules),"validation":met,"mode":mode,"radius":radius}
        zero=[k for k,v in cand.items() if v["validation"].get("candidate_predictions",0)>0 and v["validation"].get("candidate_wrong",0)==0]
        if zero:
            zero.sort(key=lambda k:(-cand[k]["validation"].get("candidate_correct",0),-cand[k]["rule_count"],k))
            selected[action]=zero[0]
        diag[action]=cand
    exact_fit=r251.fit_exact(fit)
    refit={}
    for action,k in selected.items():
        v=diag[action][k]; refit[action]=(v["mode"],v["radius"],fit_rules(fit_by[action],v["mode"],v["radius"]))
    s=Counter(); by_action=defaultdict(Counter); examples=[]
    for row in ho:
        s["transitions"]+=1
        if row["exact_key"] in exact_fit:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        if row["action"] not in refit:
            s["candidate_abstain"]+=1; continue
        mode,radius,rules=refit[row["action"]]
        p=predict(row,rules,mode)
        if p is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1; by_action[row["action"]]["predictions"]+=1
        ok=(p==row["after"])
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        by_action[row["action"]]["correct" if ok else "wrong"]+=1
        if len(examples)<30: examples.append({"trace":row["trace"],"action":row["action"],"variant":selected[row["action"]],"correct":ok})
    n=s["candidate_predictions"]; opp=s["baseline_abstain"]
    held={**dict(s),"accuracy":round(s["candidate_correct"]/n,6) if n else None,
          "coverage_of_baseline_abstain":round(n/opp,6) if opp else 0.0,
          "by_action":{a:dict(v) for a,v in by_action.items()},"examples":examples}
    gain=bool(n>0 and s["candidate_wrong"]==0 and s["candidate_correct"]>0)
    return {"selected_by_action":selected,"selection_diagnostic":diag,"heldout":held,"gain":gain}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args(); by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={g:evaluate_game(ps) for g,ps in sorted(by.items())}; agg=Counter(); gains=[]
    for g,x in games.items():
        h=x["heldout"]
        for k in ("transitions","exact_baseline","baseline_abstain","candidate_predictions","candidate_correct","candidate_wrong"): agg[k]+=int(h.get(k,0) or 0)
        if x["gain"]: gains.append(g)
    n=agg["candidate_predictions"]; opp=agg["baseline_abstain"]
    aggregate={**dict(agg),"candidate_accuracy":round(agg["candidate_correct"]/n,6) if n else None,
               "candidate_coverage_of_baseline_abstain":round(n/opp,6) if opp else 0.0,
               "gain_games":gains,"gain_game_count":len(gains),"game_count":len(games)}
    nd=bool(n>0 and agg["candidate_wrong"]==0 and agg["candidate_correct"]>0)
    out={"schema":"deus/arc3-r254-component-delta-operator/1","rung":RUNG,
         "lineage":{"r251":"run35795562246/artifact10724065280","r253":"run35797713701/artifact10724612954",
                    "repair":"relative component-anchored delta operator; no threshold-only retry"},
         "protocol":{"select":"p0-p4 fit / p5-p9 per-action zero-wrong validation","refit":"p0-p9","frozen_eval":"p10-p19","exact_baseline_precedence":True},
         "games":games,"aggregate":aggregate,"non_dominated_source_side_gain":nd,
         "promotion":{"integration_candidate":nd,"solver_promotion":False,"kaggle_packaging":False},
         "truth":{"public_trace_only":True,"game_source_read":False,"selection_uses_p0_p9_only":True,
                  "p10_p19_never_updates_selection_or_model":True,"p10_p19_status":"PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
                  "independent_generalization_claim":False,"kaggle_execution":False,"competition_submission":False,
                  "submission_quota_spent":False,"owner_score_claim":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"aggregate":aggregate,"gain":nd,"selected":{g:x["selected_by_action"] for g,x in games.items()}},sort_keys=True))

if __name__=="__main__": main()
