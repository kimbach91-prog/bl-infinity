#!/usr/bin/env python3
"""R253: source-free transition morphology diagnostic for R251 no-gain families.

Uses p0-p9 public-development traces only. This is a mechanism diagnostic, not a
predictor and not a promotion gate. It measures whether transitions look like
reusable relative operators: exact viewport shifts, global color remaps, and
repeated normalized delta patches.

It reads observed board/action transitions only. No game source, hidden data,
upstream score, Kaggle runtime or leaderboard information is used.
"""
from __future__ import annotations
import argparse, hashlib, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG=253

def sig(x:Any)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:16]

def exact_shift(before, after, bg, radius=3):
    h=len(before); w=len(before[0])
    hits=[]
    for dr in range(-radius,radius+1):
        for dc in range(-radius,radius+1):
            if dr==0 and dc==0: continue
            ok=True
            for r in range(h):
                for c in range(w):
                    sr=r-dr; sc=c-dc
                    v=before[sr][sc] if 0<=sr<h and 0<=sc<w else bg
                    if v!=after[r][c]:
                        ok=False; break
                if not ok: break
            if ok: hits.append((dr,dc))
    return hits

def transition_diag(before,after):
    h=len(before); w=len(before[0])
    changed=[]
    pair=Counter()
    mapping=defaultdict(set)
    for r in range(h):
        for c in range(w):
            b=int(before[r][c]); a=int(after[r][c])
            mapping[b].add(a)
            if b!=a:
                changed.append((r,c,b,a)); pair[(b,a)]+=1
    bg=r246.bg(before)
    if changed:
        r0=min(x[0] for x in changed); r1=max(x[0] for x in changed)
        c0=min(x[1] for x in changed); c1=max(x[1] for x in changed)
        norm=tuple(sorted((r-r0,c-c0,b,a) for r,c,b,a in changed))
        bbox=(r1-r0+1,c1-c0+1)
        touch=(r0==0 or c0==0 or r1==h-1 or c1==w-1)
        dsig=sig((bbox,norm))
    else:
        bbox=(0,0); touch=False; dsig="IDENTITY"
    shifts=exact_shift(before,after,bg)
    global_remap=all(len(v)==1 for v in mapping.values())
    return {
      "changed":len(changed),"bbox":bbox,"touch_edge":touch,
      "delta_sig":dsig,"exact_shifts":shifts,
      "global_remap":global_remap,
      "pair_top":[[list(k),v] for k,v in pair.most_common(5)],
    }

def load_rows(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        if r246.pnum(p)>=10:
            raise ValueError("R253 diagnostic is p0-p9 only")
        ev=r246.load_events(p); pre=ev[0]; step=0
        for e in ev[1:]:
            if e.get("type")!="action":
                pre=e; continue
            before=[[int(v) for v in row] for row in pre["board"]]
            after=[[int(v) for v in row] for row in e["board"]]
            if len(before)==len(after) and len(before[0])==len(after[0]):
                out.append({
                  "trace":p.name,"step":step,"action":r246.action_name(e),
                  "diag":transition_diag(before,after)
                })
                step+=1
            pre=e
    return out

def summarize(rows):
    by=defaultdict(list)
    for r in rows: by[r["action"]].append(r)
    actions={}
    for action,rs in sorted(by.items()):
        ch=[x["diag"]["changed"] for x in rs]
        nonid=[x for x in rs if x["diag"]["changed"]>0]
        ds=Counter(x["diag"]["delta_sig"] for x in nonid)
        shifts=Counter(tuple(s) for x in rs for s in x["diag"]["exact_shifts"])
        remap=sum(bool(x["diag"]["global_remap"]) for x in rs)
        actions[action]={
          "transitions":len(rs),
          "identity":sum(v==0 for v in ch),
          "changed_median":statistics.median(ch) if ch else 0,
          "changed_p90":sorted(ch)[max(0,int(.9*len(ch))-1)] if ch else 0,
          "edge_touch_fraction":round(sum(x["diag"]["touch_edge"] for x in nonid)/len(nonid),6) if nonid else 0.0,
          "global_remap_fraction":round(remap/len(rs),6) if rs else 0.0,
          "exact_shift_hits":{f"{k[0]},{k[1]}":v for k,v in shifts.most_common()},
          "nonidentity_delta_signature_count":len(ds),
          "top_delta_signatures":[[k,v] for k,v in ds.most_common(8)],
          "top_delta_reuse_fraction":round(ds.most_common(1)[0][1]/len(nonid),6) if nonid else 0.0,
        }
    return actions

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={}
    for gid,ps in sorted(by.items()):
        nums=sorted(r246.pnum(p) for p in ps)
        if nums!=list(range(10)):
            raise ValueError(f"{gid}: exact p0..p9 required, got {nums}")
        rows=load_rows(ps)
        games[gid]={"transition_count":len(rows),"actions":summarize(rows)}
    out={
      "schema":"deus/arc3-r253-transition-morphology-diagnostic/1",
      "rung":RUNG,
      "protocol":{"diagnostic_scope":"p0-p9 only","promotion":False},
      "games":games,
      "truth":{
        "public_trace_only":True,"game_source_read":False,
        "p10_p19_read":False,"independent_generalization_claim":False,
        "kaggle_execution":False,"competition_submission":False,
        "owner_score_claim":False
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    compact={}
    for g,x in games.items():
        compact[g]={a:{
          "n":m["transitions"],"medchg":m["changed_median"],
          "reuse":m["top_delta_reuse_fraction"],
          "shift":m["exact_shift_hits"],"remap":m["global_remap_fraction"]
        } for a,m in x["actions"].items()}
    print(json.dumps(compact,sort_keys=True))

if __name__=="__main__": main()
