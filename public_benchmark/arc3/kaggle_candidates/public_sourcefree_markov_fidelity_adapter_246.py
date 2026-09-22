#!/usr/bin/env python3
"""R246: bounded source-free Markov-fidelity adapter over public ARC-AGI-3 traces.

Grounding:
- Clean-room implementation of the public OpenWorld E134 idea: compare multiple
  observation lenses by Markov fidelity instead of assuming one representation.
- Compose that with DEUS's conservative executable-world-model rule: exact
  visible-state/action lookup has precedence; an abstraction may act only when
  the exact baseline abstains, and only when training maps the abstract
  (state, action) to ONE exact next frame with cross-state support.

Protocol per game:
  p0-p4  : fit exact + lens transition tables
  p5-p9  : select lens using ZERO-WRONG exact-frame added predictions first,
           then added-correct count, then Markov fidelity
  p0-p9  : refit selected lens
  p10-p19: frozen public-development evaluation

The adapter reads only observed frame/action transitions. It imports no game
source, upstream ARC game implementation, upstream replay bank, or score.
p10-p19 has been reused elsewhere in this project, so this is SOURCE-SIDE
stability evidence, NOT independent generalization or Kaggle evidence.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Callable

RUNG=246
LENS_NAMES=("palette","meter","symmetry","regions","objects","composite")
MIN_SUPPORT=2

def stable(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True)

def digest(x:Any)->str:
    return hashlib.sha256(stable(x).encode()).hexdigest()

def pnum(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1

def game_id(p:Path)->str:
    m=re.match(r"(.+)_p\d+_events\.jsonl$",p.name)
    return m.group(1) if m else p.stem

def load_events(path:Path)->list[dict]:
    out=[]
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip(): continue
        o=json.loads(raw)
        if o.get("type") in {"initial","action"} and isinstance(o.get("board"),list):
            out.append(o)
    if len(out)<2: raise ValueError(f"{path}: insufficient events")
    return out

def action_name(e:dict)->str:
    return str(e.get("action_display") or e.get("action_name") or "")

def bg(board:list[list[int]])->int:
    c=Counter(int(v) for row in board for v in row)
    return min(c,key=lambda k:(-c[k],k))

def palette(board):
    c=Counter(int(v) for row in board for v in row)
    return tuple(sorted(c.items()))

def meter(board):
    b=bg(board)
    return tuple(sorted({int(v) for v in board[0] if int(v)!=b}))

def symmetry(board):
    h=len(board);w=len(board[0])
    hs=all(board[r][c]==board[r][w-1-c] for r in range(h) for c in range(w))
    vs=all(board[r][c]==board[h-1-r][c] for r in range(h) for c in range(w))
    ds=(h==w and all(board[r][c]==board[c][r] for r in range(h) for c in range(w)))
    broken=0
    if not hs: broken+=sum(board[r][c]!=board[r][w-1-c] for r in range(h) for c in range(w))//2
    if not vs: broken+=sum(board[r][c]!=board[h-1-r][c] for r in range(h) for c in range(w))//2
    if h==w and not ds: broken+=sum(board[r][c]!=board[c][r] for r in range(h) for c in range(w))//2
    return (hs,vs,ds,broken)

def regions(board,G=8):
    b=bg(board);h=len(board);w=len(board[0]);out=[]
    for gi in range(G):
        row=[]
        r0=gi*h//G;r1=(gi+1)*h//G
        for gj in range(G):
            c0=gj*w//G;c1=(gj+1)*w//G
            vals=[board[r][c] for r in range(r0,r1) for c in range(c0,c1) if board[r][c]!=b]
            if not vals: row.append(b)
            else:
                cc=Counter(vals);row.append(min(cc,key=lambda k:(-cc[k],k)))
        out.append(tuple(row))
    return tuple(out)

def object_key(board):
    b=bg(board);h=len(board);w=len(board[0]);seen=set();objs=[]
    for r in range(h):
        for c in range(w):
            if board[r][c]==b or (r,c) in seen: continue
            color=board[r][c];q=deque([(r,c)]);seen.add((r,c));pts=[]
            while q:
                rr,cc=q.popleft();pts.append((rr,cc))
                for nr,nc in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and board[nr][nc]==color:
                        seen.add((nr,nc));q.append((nr,nc))
            rs=[x for x,y in pts];cs=[y for x,y in pts]
            objs.append((int(color),len(pts),min(rs),min(cs),max(rs)-min(rs)+1,max(cs)-min(cs)+1))
    return tuple(sorted(objs))

def lens(name:str,board):
    if name=="palette": return palette(board)
    if name=="meter": return meter(board)
    if name=="symmetry": return symmetry(board)
    if name=="regions": return regions(board)
    if name=="objects": return object_key(board)
    if name=="composite":
        return (palette(board),meter(board),symmetry(board),regions(board),object_key(board))
    raise KeyError(name)

def transitions(paths:list[Path])->list[dict]:
    out=[]
    for p in paths:
        ev=load_events(p);pre=ev[0]
        for e in ev[1:]:
            if e.get("type")!="action":
                pre=e;continue
            before=[[int(v) for v in row] for row in pre["board"]]
            after=[[int(v) for v in row] for row in e["board"]]
            if len(before)==len(after) and len(before[0])==len(after[0]):
                out.append({"trace":p.name,"before":before,"after":after,"action":action_name(e)})
            pre=e
    return out

def exact_key(r):
    return digest({"b":r["before"],"a":r["action"]})

def fit_exact(rows):
    obs=defaultdict(Counter);ex={}
    for r in rows:
        k=exact_key(r);d=digest(r["after"]);obs[k][d]+=1;ex[(k,d)]=r["after"]
    tab={}
    for k,c in obs.items():
        if len(c)==1:
            d=next(iter(c));tab[k]=ex[(k,d)]
    return tab

def fit_lens(rows,name,min_support=MIN_SUPPORT):
    # abstract state/action -> exact next-frame outcome, requiring:
    #   - one exact next frame only
    #   - support from >=2 distinct exact pre-state digests
    obs=defaultdict(Counter);prestates=defaultdict(set);ex={}
    for r in rows:
        k=stable((lens(name,r["before"]),r["action"]))
        d=digest(r["after"]);obs[k][d]+=1;prestates[k].add(digest(r["before"]));ex[(k,d)]=r["after"]
    tab={}
    for k,c in obs.items():
        if len(c)!=1 or len(prestates[k])<min_support: continue
        d=next(iter(c));tab[k]=ex[(k,d)]
    return tab

def markov_fidelity(rows,name):
    table=defaultdict(set);keys=set()
    for r in rows:
        sk=stable(lens(name,r["before"]));nk=stable(lens(name,r["after"]))
        keys.add(sk);keys.add(nk);table[(sk,r["action"])].add(nk)
    if len(keys)<2 or not table:return 0.0
    return sum(len(v)==1 for v in table.values())/len(table)

def eval_added(rows,exact,abstract,name):
    s=Counter();examples=[]
    for r in rows:
        s["transitions"]+=1
        if exact_key(r) in exact:
            s["exact_baseline"]+=1;continue
        s["baseline_abstain"]+=1
        k=stable((lens(name,r["before"]),r["action"]))
        pred=abstract.get(k)
        if pred is None:
            s["candidate_abstain"]+=1;continue
        s["candidate_predictions"]+=1
        ok=pred==r["after"]
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        if len(examples)<20:
            examples.append({"trace":r["trace"],"action":r["action"],"correct":ok})
    p=s["candidate_predictions"];opp=s["baseline_abstain"]
    return {**dict(s),
      "accuracy":round(s["candidate_correct"]/p,6) if p else None,
      "coverage_of_baseline_abstain":round(p/opp,6) if opp else 0.0,
      "examples":examples}

def select(train,val):
    exact=fit_exact(train);cand={}
    for name in LENS_NAMES:
        tab=fit_lens(train,name)
        met=eval_added(val,exact,tab,name)
        cand[name]={"keys":len(tab),"fidelity":round(markov_fidelity(train,name),6),"validation":met}
    zero=[n for n in LENS_NAMES if cand[n]["validation"].get("candidate_predictions",0)>0 and cand[n]["validation"].get("candidate_wrong",0)==0]
    if not zero:return None,cand
    zero.sort(key=lambda n:(-cand[n]["validation"].get("candidate_correct",0),
                            -cand[n]["fidelity"],LENS_NAMES.index(n)))
    return zero[0],cand

def evaluate_game(paths):
    ps=sorted(paths,key=pnum)
    nums=[pnum(p) for p in ps]
    if nums!=list(range(20)):raise ValueError(f"{game_id(ps[0])}: exact p0..p19 required, got {nums}")
    tr=transitions(ps[:5]);va=transitions(ps[5:10]);fit=transitions(ps[:10]);ho=transitions(ps[10:])
    selected,candidates=select(tr,va)
    if selected is None:
        return {"selected":None,"candidate_summary":candidates,"heldout":None,"gain":False}
    exact=fit_exact(fit);abstract=fit_lens(fit,selected)
    held=eval_added(ho,exact,abstract,selected)
    gain=bool(held.get("candidate_predictions",0)>0 and held.get("candidate_wrong",0)==0)
    return {
      "selected":selected,
      "selection":{"train_fidelity":round(markov_fidelity(fit,selected),6),
                   "candidate_summary":candidates},
      "refit":{"exact_keys":len(exact),"abstract_keys":len(abstract)},
      "heldout":held,
      "gain":gain}

def run(paths):
    by=defaultdict(list)
    for p in paths:by[game_id(p)].append(p)
    games={g:evaluate_game(ps) for g,ps in sorted(by.items())}
    agg=Counter()
    gain_games=[]
    for g,x in games.items():
        h=x.get("heldout") or {}
        for k in ("transitions","exact_baseline","baseline_abstain","candidate_predictions","candidate_correct","candidate_wrong"):
            agg[k]+=int(h.get(k,0) or 0)
        if x.get("gain"):gain_games.append(g)
    p=agg["candidate_predictions"];opp=agg["baseline_abstain"]
    aggregate={**dict(agg),
      "candidate_accuracy":round(agg["candidate_correct"]/p,6) if p else None,
      "candidate_coverage_of_baseline_abstain":round(p/opp,6) if opp else 0.0,
      "gain_games":gain_games,"gain_game_count":len(gain_games),"game_count":len(games)}
    nondominated=bool(p>0 and agg["candidate_wrong"]==0 and agg["candidate_correct"]>0)
    return {
      "schema":"deus/arc3-r246-sourcefree-markov-fidelity-adapter/1",
      "rung":RUNG,
      "grounding":{
        "openworld_repo":"quome-cloud/openworld",
        "openworld_commit":"e8248685e4f682dd6587e1af6296733cf3838a59",
        "e133_blob":"a40b164605e2d897cfeaf1384715dabb3cb6e4c9",
        "e134_composite_blob":"f234b26020afdfdd7b71d40db1189f3183561305",
        "e134_perceptors_blob":"171126c25863390e7891614dd8004ebac7f0ac7c",
        "clean_room":True},
      "protocol":{"select":"p0-p4 fit / p5-p9 zero-wrong validation",
                  "refit":"p0-p9","frozen_eval":"p10-p19",
                  "baseline":"exact visible-state/action exact-next-frame",
                  "candidate":"selected abstract lens/action -> unique exact next-frame with >=2 distinct pre-state support"},
      "games":games,"aggregate":aggregate,
      "non_dominated_source_side_gain":nondominated,
      "promotion":{"integration_candidate":nondominated,"solver_promotion":False,"kaggle_packaging":False,
                   "reason":"source-free public-trace exact-frame adapter only; reused public development is not independent provider evidence"},
      "truth":{"public_trace_only":True,"game_source_read":False,"upstream_game_source_imported":False,
               "upstream_replay_bank_imported":False,"upstream_score_imported":False,
               "lens_mechanics_clean_room_reimplemented":True,
               "selection_uses_p0_p9_only":True,"frozen_p10_p19_never_updates_model_or_selection":True,
               "p10_p19_status":"PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
               "independent_generalization_claim":False,"kaggle_execution":False,
               "submission_quota_spent":False,"owner_score_claim":False}}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"aggregate":d["aggregate"],"gain":d["non_dominated_source_side_gain"],
      "gain_games":d["aggregate"]["gain_games"],
      "selected":{g:x["selected"] for g,x in d["games"].items()}},sort_keys=True))
if __name__=="__main__":main()
