#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314
import public_tr87_wa30_region_context_loto_321 as r321
RUNG=323; GAME="tr87-cd924810"; BASE="delta"; GRID=8; MIN_NESTED_PRED=2

def key_stats(rows,rules):
    st=defaultdict(Counter)
    for row in rows:
        b=row["b"]; a=row["a"]; keys=row["keys"]; h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=keys[r][c]
                if k not in rules: continue
                p=int(rules[k]); bv=int(b[r][c]); av=int(a[r][c])
                if p==bv: continue
                st[k]["predictions"]+=1
                st[k]["correct" if p==av and bv!=av else "wrong"]+=1
    return st

def nested_trust(train):
    agg=defaultdict(Counter)
    for held in range(len(train)):
        sub=[train[i] for i in range(len(train)) if i!=held]
        rules,_=r314._fit_rules(sub); st=key_stats(train[held],rules)
        for k,c in st.items(): agg[k].update(c)
    trusted={k for k,c in agg.items() if c["predictions"]>=MIN_NESTED_PRED and c["wrong"]==0}
    return trusted,agg

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact tr87 p0-p4 required")
    raw=[r302.augment_trace(p) for p in ps]; prepared=[r321.prep(t,BASE,GRID) for t in raw]
    total=Counter(); folds=[]
    for held in range(5):
        train=[prepared[i] for i in range(5) if i!=held]
        trusted,nested=nested_trust(train); rules,fit=r314._fit_rules(train); rules={k:v for k,v in rules.items() if k in trusted}
        ev=r314._evaluate(prepared[held],rules)
        folds.append({"held_trace":held,"trusted_keys":len(trusted),"nested_predictions":sum(c["predictions"] for c in nested.values()),"nested_wrong":sum(c["wrong"] for c in nested.values()),"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]; total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    gate=bool(total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0 and total.get("exact_frame_gain",0)>=0)
    verdict="REGION8_NESTED_ZERO_FALSE_LOTO_SIGNAL" if gate else ("REGION8_NESTED_GAIN_WITH_FALSE_CHANGE" if total.get("pixel_gain",0)>0 else "NO_SIGNAL")
    out={"schema":"deus/arc3-r323-tr87-region8-nested-verifier/1","rung":RUNG,"game":GAME,
      "lineage":{"r321_run":35830964852,"region8_selected_for_repair":True},
      "protocol":{"data":"p0-p4 only","outer":"5-fold LOTO","inner":"nested training-only zero-wrong key verifier","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},
      "loto":dict(total),"folds":folds,"gate_pass":gate,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"verdict":verdict,"gate_pass":gate,"loto":out["loto"]},sort_keys=True))
if __name__=="__main__": main()
