#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_action_canonical_topology_diag_275 as r275
import public_relational_topology_diag_274 as r274

RUNG=322; GAME="ft09-0d8bbf25"; MIN_PRESTATES=2; MIN_TRACES=2
MODES=("canon_masked_raw","canon_meter","canon_regions","canon_nodes","canon_graph")

def canon_key_board(board,action): return r275.canon_board(board,action,use_ui_mask=True)
def canon_full(board,action): return r275.canon_board(board,action,use_ui_mask=False)

def rep(r,m):
    b=canon_key_board(r["before"],r["action"])
    if m=="canon_masked_raw": x=b
    elif m=="canon_meter": x=r246.meter(b)
    elif m=="canon_regions": x=r246.regions(b)
    elif m=="canon_nodes": x=r274.desc(b,"nodes_coarse")
    elif m=="canon_graph": x=r274.desc(b,"graph_coarse_noedge")
    else: raise KeyError(m)
    return r246.stable((x,r275.action_class(r["action"])))

def exact_key(r): return r246.digest({"b":r["before"],"a":r["action"]})
def target_digest(r): return r246.digest(canon_full(r["after"],r["action"]))

def fit_exact(rows):
    obs=defaultdict(Counter)
    for r in rows: obs[exact_key(r)][r["after_digest"]]+=1
    return {k for k,c in obs.items() if len(c)==1}

def fit_abs(rows,m):
    obs=defaultdict(Counter); pre=defaultdict(set); trs=defaultdict(set); frame={}
    for r in rows:
        k=rep(r,m); d=target_digest(r); obs[k][d]+=1; pre[k].add(r["before_digest"]); trs[k].add(r["trace"]); frame[(k,d)]=canon_full(r["after"],r["action"])
    tab={}
    for k,c in obs.items():
        if len(c)!=1 or len(pre[k])<MIN_PRESTATES or len(trs[k])<MIN_TRACES: continue
        d=next(iter(c)); tab[k]=frame[(k,d)]
    return tab

def ev(rows,exact,tab,m):
    s=Counter()
    for r in rows:
        s["transitions"]+=1
        if exact_key(r) in exact: s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1; p=tab.get(rep(r,m))
        if p is None: s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        s["candidate_correct" if p==canon_full(r["after"],r["action"]) else "candidate_wrong"]+=1
    n=s["candidate_predictions"]; s["accuracy"]=round(s["candidate_correct"]/n,6) if n else None
    return dict(s)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact p0-p4 required")
    traces=[r251.prepare_rows([p]) for p in ps]; totals={m:Counter() for m in MODES}
    for held in range(5):
        train=[r for i,tr in enumerate(traces) if i!=held for r in tr]; val=traces[held]; exact=fit_exact(train)
        for m in MODES:
            met=ev(val,exact,fit_abs(train,m),m)
            for k,v in met.items():
                if isinstance(v,int): totals[m][k]+=v
    modes={}; cand=[]
    for m,s in totals.items():
        n=s["candidate_predictions"]; modes[m]={**dict(s),"accuracy":round(s["candidate_correct"]/n,6) if n else None}
        if n>0 and s["candidate_wrong"]==0 and s["candidate_correct"]>0: cand.append(m)
    best=max(cand,key=lambda m:(modes[m]["candidate_correct"],modes[m]["candidate_predictions"])) if cand else None
    verdict="ACTION_CANONICAL_ZERO_WRONG_EXACTFRAME_SIGNAL" if best else "NO_SIGNAL"
    out={"schema":"deus/arc3-r322-ft09-action-canonical-exactframe-loto/1","rung":RUNG,"game":GAME,
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold LOTO","directional_pooling":"rotate to UP and pool as MOVE","candidate_target":"exact full canonical next frame","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},
      "modes":modes,"candidate_modes":cand,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))
if __name__=="__main__": main()
