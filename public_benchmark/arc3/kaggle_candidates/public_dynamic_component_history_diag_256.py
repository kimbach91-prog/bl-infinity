#!/usr/bin/env python3
"""R256: source-free dynamic-component + temporal-history diagnostic for re86.

R255 falsified global viewport translation: identity is materially closer to the
next frame than any small whole-frame shift. R256 changes representation rather
than thresholds. It asks whether the transition is instead dominated by a small
moving foreground component on a mostly screen-fixed scene, and whether recent
change-mask history improves localization/predictability.

Protocol: read exact public p0-p9 only. Diagnostic-only. No p10-p19 access,
no game source, no Kaggle execution, no promotion.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG=256
RADIUS=4

def changed(before, after):
    return {(r,c) for r,row in enumerate(before) for c,v in enumerate(row) if int(v)!=int(after[r][c])}

def edge_fraction(mask,h,w):
    if not mask: return 0.0
    return sum(r in (0,h-1) or c in (0,w-1) for r,c in mask)/len(mask)

def components(mask):
    left=set(mask); sizes=[]
    while left:
        q=[left.pop()]; n=0
        while q:
            r,c=q.pop(); n+=1
            for p in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if p in left:
                    left.remove(p); q.append(p)
        sizes.append(n)
    return sorted(sizes, reverse=True)

def shifted_mask(mask,dr,dc,h,w):
    return {(r+dr,c+dc) for r,c in mask if 0<=r+dr<h and 0<=c+dc<w}

def iou(a,b):
    if not a and not b: return 1.0
    u=len(a|b)
    return len(a&b)/u if u else 0.0

def best_mask_track(prev_mask,cur_mask,h,w):
    if prev_mask is None or not prev_mask or not cur_mask:
        return {"unshifted_iou":0.0,"best_iou":0.0,"best_shift":[0,0],"improvement":0.0}
    base=iou(prev_mask,cur_mask); best=(base,0,0)
    for dr in range(-RADIUS,RADIUS+1):
        for dc in range(-RADIUS,RADIUS+1):
            if dr==0 and dc==0: continue
            s=iou(shifted_mask(prev_mask,dr,dc,h,w),cur_mask)
            if (s,-abs(dr)-abs(dc),-dr,-dc) > (best[0],-abs(best[1])-abs(best[2]),-best[1],-best[2]):
                best=(s,dr,dc)
    return {"unshifted_iou":base,"best_iou":best[0],"best_shift":[best[1],best[2]],"improvement":best[0]-base}

def best_foreground_transport(before,after,mask):
    h=len(before); w=len(before[0]); bg=r246.bg(before)
    src=[(r,c) for r,c in mask if int(before[r][c])!=int(bg)]
    tgt=[(r,c) for r,c in mask if int(after[r][c])!=int(bg)]
    if not src and not tgt:
        return {"best_shift":[0,0],"score":0.0,"src_support":0,"tgt_support":0,"src_match":0,"tgt_match":0}
    best=(-1.0,-1,-1,0,0,0,0)
    for dr in range(-RADIUS,RADIUS+1):
        for dc in range(-RADIUS,RADIUS+1):
            if dr==0 and dc==0: continue
            sm=0
            for r,c in src:
                rr=r+dr; cc=c+dc
                if 0<=rr<h and 0<=cc<w and (rr,cc) in mask and int(after[rr][cc])==int(before[r][c]):
                    sm+=1
            tm=0
            for r,c in tgt:
                rr=r-dr; cc=c-dc
                if 0<=rr<h and 0<=cc<w and (rr,cc) in mask and int(before[rr][cc])==int(after[r][c]):
                    tm+=1
            denom=max(1,len(src)+len(tgt)); score=(sm+tm)/denom
            key=(score,sm+tm,-abs(dr)-abs(dc),-abs(dr),-abs(dc),-dr,-dc)
            if key>best:
                best=(score,sm+tm,-abs(dr)-abs(dc),dr,dc,sm,tm)
    return {"best_shift":[best[3],best[4]],"score":best[0],"src_support":len(src),"tgt_support":len(tgt),"src_match":best[5],"tgt_match":best[6]}

def q(vals,p):
    if not vals: return 0.0
    s=sorted(vals); i=min(len(s)-1,max(0,int(p*len(s))))
    return float(s[i])

def median(vals): return float(statistics.median(vals)) if vals else 0.0

def mode_pairs(vals,n=8): return [[list(k),v] for k,v in Counter(vals).most_common(n)]

def purity(rows,key_fn):
    groups=defaultdict(list)
    for x in rows:
        if x["fg"]["score"]<=0: continue
        groups[key_fn(x)].append(tuple(x["fg"]["best_shift"]))
    good=tot=0
    for xs in groups.values():
        tot+=len(xs); good+=Counter(xs).most_common(1)[0][1]
    return good/tot if tot else 0.0

def summarize(rows):
    by=defaultdict(list)
    for x in rows: by[x["action"]].append(x)
    out={}
    for act,xs in sorted(by.items()):
        fg=[x["fg"]["score"] for x in xs if x["changed_cells"]>0]
        tr=[x["track"]["best_iou"] for x in xs if x["has_prev_delta"]]
        imp=[x["track"]["improvement"] for x in xs if x["has_prev_delta"]]
        cc=[x["component_count"] for x in xs if x["changed_cells"]>0]
        top=[x["top_component_fraction"] for x in xs if x["changed_cells"]>0]
        out[act]={
            "transitions":len(xs),
            "nonidentity":sum(x["changed_cells"]>0 for x in xs),
            "median_changed_cells":median([x["changed_cells"] for x in xs]),
            "median_edge_fraction":round(median([x["edge_fraction"] for x in xs if x["changed_cells"]>0]),6),
            "median_component_count":median(cc),
            "median_top_component_fraction":round(median(top),6),
            "median_foreground_transport_score":round(median(fg),6),
            "p75_foreground_transport_score":round(q(fg,0.75),6),
            "fg_transport_ge_0p5_fraction":round(sum(v>=0.5 for v in fg)/len(fg),6) if fg else 0.0,
            "modal_foreground_shifts":mode_pairs([tuple(x["fg"]["best_shift"]) for x in xs if x["fg"]["score"]>0]),
            "history_rows":len(tr),
            "median_prev_mask_best_iou":round(median(tr),6),
            "median_prev_mask_iou_improvement":round(median(imp),6),
            "prev_mask_best_iou_ge_0p5_fraction":round(sum(v>=0.5 for v in tr)/len(tr),6) if tr else 0.0,
            "modal_prev_mask_track_shifts":mode_pairs([tuple(x["track"]["best_shift"]) for x in xs if x["has_prev_delta"]]),
        }
    hist={
        "shift_purity_action":round(purity(rows,lambda x:(x["action"],)),6),
        "shift_purity_action_prev":round(purity(rows,lambda x:(x["action"],x["prev_action"])),6),
        "shift_purity_action_prev_runbin":round(purity(rows,lambda x:(x["action"],x["prev_action"],min(x["action_run_length"],4))),6),
    }
    return out,hist

def rows(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        if r246.pnum(p)>=10: raise ValueError("R256 is p0-p9 only")
        ev=r246.load_events(p); pre=ev[0]; prev_action="START"; runlen=0; prev_mask=None; step=0
        for e in ev[1:]:
            if e.get("type")!="action": pre=e; continue
            action=r246.action_name(e)
            runlen=runlen+1 if action==prev_action else 1
            b=[[int(v) for v in row] for row in pre["board"]]
            a=[[int(v) for v in row] for row in e["board"]]
            if len(b)==len(a) and len(b[0])==len(a[0]):
                h=len(b); w=len(b[0]); m=changed(b,a); cs=components(m)
                fg=best_foreground_transport(b,a,m)
                tr=best_mask_track(prev_mask,m,h,w)
                out.append({
                    "trace":p.name,"step":step,"action":action,"prev_action":prev_action,
                    "action_run_length":runlen,"changed_cells":len(m),"edge_fraction":edge_fraction(m,h,w),
                    "component_count":len(cs),"top_component_fraction":((cs[0]/len(m)) if m else 0.0),
                    "fg":fg,"has_prev_delta":prev_mask is not None,"track":tr,
                })
                prev_mask=m
            prev_action=action; pre=e; step+=1
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f"exact p0..p9 required, got {nums}")
    rs=rows(ps); by,hist=summarize(rs)
    fg_all=[x["fg"]["score"] for x in rs if x["changed_cells"]>0]
    track_all=[x["track"]["best_iou"] for x in rs if x["has_prev_delta"]]
    verdict="DYNAMIC_COMPONENT_SUPPORTED" if (median(fg_all)>=0.35 or median(track_all)>=0.35) else "DYNAMIC_COMPONENT_WEAK"
    out={
        "schema":"deus/arc3-r256-dynamic-component-history-diagnostic/1","rung":RUNG,
        "protocol":{"scope":"p0-p9 only","radius":RADIUS,"promotion":False},
        "summary":by,"history_conditioning":hist,
        "overall":{
            "transitions":len(rs),"median_foreground_transport_score":round(median(fg_all),6),
            "median_prev_mask_best_iou":round(median(track_all),6),"verdict":verdict,
        },
        "truth":{"public_trace_only":True,"game_source_read":False,"p10_p19_read":False,"independent_generalization_claim":False,"kaggle_execution":False,"competition_submission":False,"owner_score_claim":False},
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"overall":out["overall"],"history_conditioning":hist,"summary":by},sort_keys=True))
if __name__=="__main__": main()
