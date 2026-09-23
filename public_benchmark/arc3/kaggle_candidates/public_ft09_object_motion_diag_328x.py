#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_action_canonical_topology_diag_275 as r275
import public_relational_topology_diag_274 as r274
RUNG="328X"; GAME="ft09-0d8bbf25"
def objs(board,action):
    b=r275.canon_board(board,action,use_ui_mask=True)
    xs,_,_=r274.extract(b,False)
    return xs
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)):raise SystemExit("exact ft09 p0-p4 required")
    byclass=defaultdict(Counter);matched=Counter();examples=[]
    for p in ps:
      for row in r251.prepare_rows([p]):
        before=objs(row["before"],row["action"]);after=objs(row["after"],row["action"]);bg=defaultdict(list);ag=defaultdict(list)
        for o in before:bg[o["exact"]].append(o)
        for o in after:ag[o["exact"]].append(o)
        ac=r275.action_class(row["action"])
        for sig,bv in bg.items():
          av=ag.get(sig,[])
          if len(bv)!=1 or len(av)!=1:continue
          dy=round(av[0]["cy"]-bv[0]["cy"]);dx=round(av[0]["cx"]-bv[0]["cx"])
          matched[ac]+=1
          byclass[ac][(dy,dx)]+=1
          if len(examples)<30 and (dy or dx):examples.append({"trace":row["trace"],"action":row["action"],"class":ac,"vector":[dy,dx],"sig":list(sig)})
    classes={};signals=[]
    for ac,c in sorted(byclass.items()):
      total=sum(c.values());top=c.most_common(5);nonzero=sum(n for (v,n) in c.items() if v!=(0,0))
      best_nonzero=max(((n,v) for v,n in c.items() if v!=(0,0)),default=(0,None))
      share=best_nonzero[0]/total if total else 0
      classes[ac]={"matched":total,"nonzero":nonzero,"top_vectors":[{"vector":list(v),"count":n} for v,n in top],"best_nonzero_vector":list(best_nonzero[1]) if best_nonzero[1] else None,"best_nonzero_share":round(share,6)}
      if total>=20 and best_nonzero[0]>=10 and share>=0.6:signals.append(ac)
    verdict="ACTION_CANONICAL_OBJECT_MOTION_SIGNAL" if signals else "NO_DOMINANT_OBJECT_MOTION_SIGNAL"
    out={"schema":"deus/arc3-r328x-ft09-object-motion-diagnostic/1","rung":RUNG,"game":GAME,"protocol":{"data":"p0-p4 only","diagnostic_only":True,"p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},"classes":classes,"signal_classes":signals,"examples":examples,"verdict":verdict,"truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps({"verdict":verdict,"signal_classes":signals,"classes":classes},sort_keys=True))
if __name__=="__main__":main()
