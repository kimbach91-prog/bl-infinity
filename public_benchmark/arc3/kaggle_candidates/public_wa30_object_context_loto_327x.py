#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_wa30_ft09_object_residual_loto_324 as r324
RUNG="327X"; GAME="wa30-ee6fef47"; MODES=("region4","phase","region4_phase"); MIN_TRACE_SUPPORT=2
def phase(row):
    p=row.get("phase_before",("START",0))
    if isinstance(p,list): p=tuple(p)
    return tuple(p) if isinstance(p,tuple) else (str(p),0)
def key_ctx(board,o,action,row,mode):
    base=(r275.action_class(action),o["color"],len(o["pts"]),o["h"],o["w"],o["shape"],r324.ring(board,o))
    h=len(board); w=len(board[0]) if h else 0
    cy=(o["r0"]+o["r1"])//2; cx=(o["c0"]+o["c1"])//2; reg=(min(3,cy*4//max(1,h)),min(3,cx*4//max(1,w)))
    if mode=="region4": return base+(("region4",)+reg,)
    if mode=="phase": return base+(("phase",)+phase(row),)
    if mode=="region4_phase": return base+(("region4",)+reg,("phase",)+phase(row))
    raise KeyError(mode)
def fit(traces,mode):
    obs=defaultdict(Counter);sup=defaultdict(set)
    for ti,tr in enumerate(traces):
      for row in tr:
        b=r324.world(row["before"],row["action"]);a=r324.world(row["after"],row["action"])
        for o in r324.comps(b):
          t=r324.templ(b,a,o)
          if not t: continue
          k=key_ctx(b,o,row["action"],row,mode);obs[k][t]+=1;sup[k].add(ti)
    rules={k:next(iter(c)) for k,c in obs.items() if len(c)==1 and len(sup[k])>=MIN_TRACE_SUPPORT}
    return rules,{"keys_with_change":len(obs),"accepted_templates":len(rules)}
def ev(rows,rules,mode):
    m=Counter()
    for row in rows:
      b=r324.world(row["before"],row["action"]);a=r324.world(row["after"],row["action"]);h=len(b);w=len(b[0]) if h else 0;prop=defaultdict(set)
      for o in r324.comps(b):
        t=rules.get(key_ctx(b,o,row["action"],row,mode))
        if t is None:continue
        ok=True
        for dr,dc,bv,av in t:
          rr=o["r0"]+dr;cc=o["c0"]+dc
          if not(0<=rr<h and 0<=cc<w and int(b[rr][cc])==bv):ok=False;break
        if not ok:continue
        for dr,dc,bv,av in t:prop[(o["r0"]+dr,o["c0"]+dc)].add(int(av))
      pred=[list(map(int,x)) for x in b]
      for (r,c),vals in prop.items():
        if len(vals)==1:pred[r][c]=next(iter(vals))
      ie=ce=0
      for r in range(h):
        for c in range(w):
          bv=int(b[r][c]);av=int(a[r][c]);pv=int(pred[r][c]);ie+=bv!=av;ce+=pv!=av
          if pv!=bv:
            m["predicted_changes"]+=1
            if pv==av and bv!=av:m["true_changed_correct"]+=1
            elif pv!=av:m["false_changes"]+=1
      m["frames"]+=1;m["identity_errors"]+=ie;m["candidate_errors"]+=ce;m["identity_exact_frames"]+=ie==0;m["candidate_exact_frames"]+=ce==0
    m["pixel_gain"]=m["identity_errors"]-m["candidate_errors"];m["exact_frame_gain"]=m["candidate_exact_frames"]-m["identity_exact_frames"]
    return dict(m)
def run(traces,mode):
    total=Counter()
    for held in range(5):
      train=[traces[i] for i in range(5) if i!=held];rules,_=fit(train,mode);x=ev(traces[held],rules,mode)
      for k,v in x.items():
        if isinstance(v,int):total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"];total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)):raise SystemExit("exact wa30 p0-p4 required")
    traces=[r278.annotated_rows([p]) for p in ps];modes={m:run(traces,m) for m in MODES}
    cand=[m for m,v in modes.items() if v.get("predicted_changes",0)>0 and v.get("false_changes",0)==0 and v.get("pixel_gain",0)>0 and v.get("exact_frame_gain",0)>=0]
    best=max(cand,key=lambda m:(modes[m].get("exact_frame_gain",0),modes[m].get("pixel_gain",0))) if cand else None
    verdict="OBJECT_CONTEXT_ZERO_FALSE_LOTO_SIGNAL" if best else ("OBJECT_CONTEXT_GAIN_WITH_FALSE_CHANGE" if any(v.get("pixel_gain",0)>0 for v in modes.values()) else "NO_SIGNAL")
    out={"schema":"deus/arc3-r327x-wa30-object-context-loto/1","rung":RUNG,"game":GAME,"modes":modes,"best_mode":best,"verdict":verdict,"protocol":{"data":"p0-p4 only","evaluation":"5-fold LOTO","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},"truth":{"public_trace_only":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps({"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))
if __name__=="__main__":main()
