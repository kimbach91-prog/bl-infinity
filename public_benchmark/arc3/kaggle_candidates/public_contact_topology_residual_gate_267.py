#!/usr/bin/env python3
"""R267: source-free contact-topology residual gate for re86.

R264 verified post-transport residuals are object-relative.
R265 generic sparse object-offset corrections and R266 exact local-context rules
did not promote. R267 compresses interaction context into contact topology:
overlap/contact counts, directional obstacle distance, edge proximity, source
contact, and object identity at several granularities.

Protocol:
  p0-p4 fit
  p5-p9 per-action zero-wrong selection
  p0-p9 refit
  p10-p19 frozen reused public-development evaluation

No game source, hidden state, Kaggle score, leaderboard data or submission.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_selective_object_transport_257 as r257

RUNG=267
MAX_AREA=13
MIN_FRAC=.8
MIN_SUPPORT=3
IDENTITIES=("full","geom","area")
CONTEXTS=("dest","dest_edge","dest_source","dest_source_color")
SUPPORTS=(2,3,4)


def prep(p):
    out=[]
    for i,r in enumerate(r251.prepare_rows([p])):
        x=dict(r); x["transition_id"]=f"{p.name}#{i}"; out.append(x)
    return out


def fit_base(rows):
    return r257.learn(rows,MAX_AREA,MIN_FRAC,MIN_SUPPORT)


def moved(board,model):
    vector,movable=model
    if not vector or not movable:return []
    dr,dc=vector; h=len(board); w=len(board[0]); out=[]
    for c in r254.components(board):
        if c["area"]>MAX_AREA or r257.cls(c) not in movable: continue
        if c["r0"]+dr<0 or c["c0"]+dc<0 or c["r1"]+dr>=h or c["c1"]+dc>=w: continue
        out.append(c)
    return out


def ident(c,mode):
    shape=r246.stable(c["shape"])
    if mode=="full": return (int(c["color"]),int(c["area"]),shape)
    if mode=="geom": return (int(c["area"]),shape)
    if mode=="area": return (int(c["area"]),)
    raise KeyError(mode)


def cleared(board,c):
    bg=int(r246.bg(board)); out=[list(map(int,row)) for row in board]
    for rr,cc in c["shape"]:
        out[c["r0"]+rr][c["c0"]+cc]=bg
    return out,bg


def target_cells(c,vector):
    dr,dc=vector
    return {(c["r0"]+rr+dr,c["c0"]+cc+dc) for rr,cc in c["shape"]}


def bbox_of(points):
    rs=[p[0] for p in points]; cs=[p[1] for p in points]
    return min(rs),min(cs),max(rs),max(cs)


def cap(x,n=4): return min(int(x),n)


def directional_distance(board,bbox,vector,bg,maxd=7):
    r0,c0,r1,c1=bbox; dr,dc=vector; h=len(board); w=len(board[0])
    for d in range(1,maxd+1):
        if dr<0:
            cells=[(r0-d,c) for c in range(c0,c1+1)]
        elif dr>0:
            cells=[(r1+d,c) for c in range(c0,c1+1)]
        elif dc<0:
            cells=[(r,c0-d) for r in range(r0,r1+1)]
        else:
            cells=[(r,c1+d) for r in range(r0,r1+1)]
        inside=[(r,c) for r,c in cells if 0<=r<h and 0<=c<w]
        if not inside: return 0
        if any(int(board[r][c])!=bg for r,c in inside): return d
    return maxd+1


def ring_counts(board,points,bg):
    pts=set(points); h=len(board); w=len(board[0])
    dirs=[(-1,0),(1,0),(0,-1),(0,1)]
    cnt=[0,0,0,0]; colors=Counter()
    for r,c in pts:
        for i,(dr,dc) in enumerate(dirs):
            nr,nc=r+dr,c+dc
            if (nr,nc) in pts or not (0<=nr<h and 0<=nc<w): continue
            v=int(board[nr][nc])
            if v!=bg:
                cnt[i]+=1; colors[v]+=1
    return tuple(cap(x) for x in cnt), tuple(sorted((int(k),cap(v)) for k,v in colors.items()))


def descriptor(row,c,model,context):
    vector=model[0]; free,bg=cleared(row["before"],c)
    src={(c["r0"]+rr,c["c0"]+cc) for rr,cc in c["shape"]}
    dst=target_cells(c,vector)
    overlap=[int(free[r][cc]) for r,cc in dst if int(free[r][cc])!=bg]
    dst_ring,dst_colors=ring_counts(free,dst,bg)
    src_ring,src_colors=ring_counts(free,src,bg)
    db=bbox_of(dst)
    edge=(min(db[0],6),min(db[1],6),min(len(free)-1-db[2],6),min(len(free[0])-1-db[3],6))
    dd=directional_distance(free,db,vector,bg)
    base=(cap(len(overlap)),dst_ring,cap(dd,8))
    if context=="dest": return base
    if context=="dest_edge": return base+(edge,)
    if context=="dest_source": return base+(edge,src_ring)
    if context=="dest_source_color":
        return base+(edge,src_ring,tuple(sorted((v,cap(n)) for v,n in Counter(overlap).items())),dst_colors,src_colors)
    raise KeyError(context)


def nearest(comps,rr,cc,vector):
    dr,dc=vector; ranked=[]
    for i,c in enumerate(comps):
        r0=c["r0"]+dr; c0=c["c0"]+dc
        cr=(r0+c["r1"]+dr)/2; co=(c0+c["c1"]+dc)/2
        ranked.append((abs(rr-cr)+abs(cc-co),i,r0,c0))
    return min(ranked) if ranked else None


def fit_rules(rows,model,identity,context,support):
    obs=defaultdict(Counter); traces=defaultdict(lambda:defaultdict(set))
    for row in rows:
        base=r257.render(row["before"],model[0],model[1],MAX_AREA)
        comps=moved(row["before"],model)
        if base is None or not comps: continue
        assigned=defaultdict(list)
        for rr in range(len(base)):
            for cc in range(len(base[0])):
                if int(base[rr][cc])==int(row["after"][rr][cc]): continue
                n=nearest(comps,rr,cc,model[0])
                if not n: continue
                _,i,r0,c0=n
                orr,occ=rr-r0,cc-c0
                if abs(orr)>12 or abs(occ)>12: continue
                assigned[i].append((orr,occ,int(row["after"][rr][cc])))
        for i,c in enumerate(comps):
            edits=tuple(sorted(set(assigned.get(i,[]))))
            if not edits: continue
            key=(row["action"],ident(c,identity),descriptor(row,c,model,context))
            obs[key][edits]+=1; traces[key][edits].add(row["trace"])
    rules={}
    for k,count in obs.items():
        if len(count)!=1: continue
        outcome=next(iter(count))
        if len(traces[k][outcome])>=support: rules[k]=outcome
    return rules


def apply(row,model,rules,identity,context):
    base=r257.render(row["before"],model[0],model[1],MAX_AREA)
    comps=moved(row["before"],model)
    if base is None or not comps:return None
    dr,dc=model[0]; proposals=defaultdict(set); matched=0
    for c in comps:
        key=(row["action"],ident(c,identity),descriptor(row,c,model,context))
        edits=rules.get(key)
        if edits is None: continue
        matched+=1; r0=c["r0"]+dr; c0=c["c0"]+dc
        for orr,occ,v in edits:
            rr,cc=r0+orr,c0+occ
            if not (0<=rr<len(base) and 0<=cc<len(base[0])): return None
            proposals[(rr,cc)].add(int(v))
    if matched==0 or any(len(v)!=1 for v in proposals.values()): return None
    out=[r[:] for r in base]
    for (rr,cc),vs in proposals.items(): out[rr][cc]=next(iter(vs))
    return out


def evaluate(rows,exact,model,rules,identity,context):
    s=Counter(); examples=[]
    for row in rows:
        s["transitions"]+=1
        if row["exact_key"] in exact:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        p=apply(row,model,rules,identity,context)
        if p is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        ok=p==row["after"]; s["candidate_correct" if ok else "candidate_wrong"]+=1
        if len(examples)<20: examples.append({"trace":row["trace"],"action":row["action"],"correct":ok})
    n=s["candidate_predictions"]; opp=s["baseline_abstain"]
    return {**dict(s),"accuracy":round(s["candidate_correct"]/n,6) if n else None,
            "coverage":round(n/opp,6) if opp else 0.0,"examples":examples}


def evaluate_game(paths):
    ps=sorted(paths,key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(20)): raise ValueError("p0..p19 required")
    parts=[prep(p) for p in ps]
    tr=[r for x in parts[:5] for r in x]; va=[r for x in parts[5:10] for r in x]
    fit=[r for x in parts[:10] for r in x]; ho=[r for x in parts[10:] for r in x]
    tr_by=defaultdict(list); va_by=defaultdict(list); fit_by=defaultdict(list)
    for r in tr: tr_by[r["action"]].append(r)
    for r in va: va_by[r["action"]].append(r)
    for r in fit: fit_by[r["action"]].append(r)
    exact_tr=r251.fit_exact(tr); selected={}; diag={}
    for action in sorted(set(tr_by)|set(va_by)):
        base=fit_base(tr_by[action]); cand={}
        for identity in IDENTITIES:
            for context in CONTEXTS:
                for support in SUPPORTS:
                    rules=fit_rules(tr_by[action],base,identity,context,support)
                    met=evaluate(va_by[action],exact_tr,base,rules,identity,context)
                    key=f"{identity}_{context}_s{support}"
                    cand[key]={"identity":identity,"context":context,"support":support,
                               "rule_count":len(rules),"base_vector":list(base[0]) if base and base[0] else None,
                               "validation":met}
        zero=[k for k,v in cand.items() if v["validation"].get("candidate_correct",0)>0 and v["validation"].get("candidate_wrong",0)==0]
        if zero:
            zero.sort(key=lambda k:(-cand[k]["validation"].get("candidate_correct",0),
                                    -cand[k]["validation"].get("candidate_predictions",0),
                                    cand[k]["rule_count"],k))
            selected[action]=zero[0]
        diag[action]=cand
    exact_fit=r251.fit_exact(fit); refit={}
    for action,key in selected.items():
        spec=diag[action][key]; base=fit_base(fit_by[action])
        rules=fit_rules(fit_by[action],base,spec["identity"],spec["context"],spec["support"])
        refit[action]=(base,rules,spec)
    s=Counter(); by_action=defaultdict(Counter); examples=[]
    for row in ho:
        s["transitions"]+=1
        if row["exact_key"] in exact_fit:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        pack=refit.get(row["action"])
        if pack is None:
            s["candidate_abstain"]+=1; continue
        base,rules,spec=pack
        p=apply(row,base,rules,spec["identity"],spec["context"])
        if p is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1; by_action[row["action"]]["predictions"]+=1
        ok=p==row["after"]; s["candidate_correct" if ok else "candidate_wrong"]+=1
        by_action[row["action"]]["correct" if ok else "wrong"]+=1
        if len(examples)<30: examples.append({"trace":row["trace"],"action":row["action"],"variant":selected[row["action"]],"correct":ok})
    n=s["candidate_predictions"]; opp=s["baseline_abstain"]
    held={**dict(s),"accuracy":round(s["candidate_correct"]/n,6) if n else None,
          "coverage":round(n/opp,6) if opp else 0.0,
          "by_action":{a:dict(v) for a,v in by_action.items()},"examples":examples}
    return {"selected_by_action":selected,"selection_diagnostic":diag,"heldout":held,
            "gain":bool(n>0 and s["candidate_wrong"]==0 and s["candidate_correct"]>0)}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={g:evaluate_game(ps) for g,ps in sorted(by.items())}; agg=Counter(); gains=[]
    for g,x in games.items():
        h=x["heldout"]
        for k in ("transitions","exact_baseline","baseline_abstain","candidate_predictions","candidate_correct","candidate_wrong"):
            agg[k]+=int(h.get(k,0) or 0)
        if x["gain"]: gains.append(g)
    n=agg["candidate_predictions"]; opp=agg["baseline_abstain"]
    aggregate={**dict(agg),"candidate_accuracy":round(agg["candidate_correct"]/n,6) if n else None,
               "candidate_coverage_of_baseline_abstain":round(n/opp,6) if opp else 0.0,
               "gain_games":gains,"gain_game_count":len(gains),"game_count":len(games)}
    nd=bool(n>0 and agg["candidate_wrong"]==0 and agg["candidate_correct"]>0)
    out={"schema":"deus/arc3-r267-contact-topology-residual-gate/1","rung":RUNG,
         "lineage":{"r264":"object-relative residual verified","r265":"generic local no-promotion","r266":"exact context no-promotion",
                    "repair":"coarse contact topology + identity granularity"},
         "protocol":{"select":"p0-p4 fit / p5-p9 per-action zero-wrong validation","refit":"p0-p9","frozen_eval":"p10-p19","exact_baseline_precedence":True},
         "games":games,"aggregate":aggregate,"non_dominated_source_side_gain":nd,
         "promotion":{"integration_candidate":nd,"solver_promotion":False,"kaggle_packaging":False},
         "truth":{"public_trace_only":True,"game_source_read":False,"selection_uses_p0_p9_only":True,
                  "p10_p19_never_updates_selection_or_model":True,
                  "p10_p19_status":"PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
                  "independent_generalization_claim":False,"kaggle_execution":False,
                  "competition_submission":False,"submission_quota_spent":False,"owner_score_claim":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"aggregate":aggregate,"gain":nd,"selected":{g:x["selected_by_action"] for g,x in games.items()}},sort_keys=True))

if __name__=="__main__": main()
