#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict,deque
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275

RUNG=324; ALLOWED={"wa30-ee6fef47","ft09-0d8bbf25"}; MARGIN=2; MIN_TRACE_SUPPORT=2
def world(board,action): return r275.canon_board(board,action,use_ui_mask=True)
def comps(board):
  h=len(board); w=len(board[0]) if h else 0; cnt=Counter(int(v) for row in board for v in row); bg=min(cnt,key=lambda k:(-cnt[k],k)) if cnt else 0
  seen=set(); out=[]
  for r in range(h):
    for c in range(w):
      col=int(board[r][c])
      if col==bg or (r,c) in seen: continue
      q=deque([(r,c)]); seen.add((r,c)); pts=[]
      while q:
        rr,cc=q.popleft(); pts.append((rr,cc))
        for nr,nc in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
          if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and int(board[nr][nc])==col:
            seen.add((nr,nc)); q.append((nr,nc))
      rs=[x for x,y in pts]; cs=[y for x,y in pts]; r0,c0,r1,c1=min(rs),min(cs),max(rs),max(cs)
      local=tuple(sorted((rr-r0,cc-c0) for rr,cc in pts))
      out.append({"color":col,"pts":pts,"r0":r0,"c0":c0,"r1":r1,"c1":c1,"h":r1-r0+1,"w":c1-c0+1,"shape":r246.digest(local)})
  return out
def ring(board,o):
  h=len(board); w=len(board[0]) if h else 0; inside=set(o["pts"]); cnt=Counter()
  for r in range(max(0,o["r0"]-MARGIN),min(h-1,o["r1"]+MARGIN)+1):
    for c in range(max(0,o["c0"]-MARGIN),min(w-1,o["c1"]+MARGIN)+1):
      if (r,c) not in inside: cnt[int(board[r][c])]+=1
  return tuple(sorted((k,min(v,15)) for k,v in cnt.items()))
def key(board,o,action): return (r275.action_class(action),o["color"],len(o["pts"]),o["h"],o["w"],o["shape"],ring(board,o))
def templ(b,a,o):
  h=len(b); w=len(b[0]) if h else 0; out=[]
  for r in range(max(0,o["r0"]-MARGIN),min(h-1,o["r1"]+MARGIN)+1):
    for c in range(max(0,o["c0"]-MARGIN),min(w-1,o["c1"]+MARGIN)+1):
      bv=int(b[r][c]); av=int(a[r][c])
      if bv!=av: out.append((r-o["r0"],c-o["c0"],bv,av))
  return tuple(sorted(out))
def fit(traces):
  obs=defaultdict(Counter); sup=defaultdict(set)
  for ti,tr in enumerate(traces):
    for row in tr:
      b=world(row["before"],row["action"]); a=world(row["after"],row["action"])
      for o in comps(b):
        t=templ(b,a,o)
        if not t: continue
        k=key(b,o,row["action"]); obs[k][t]+=1; sup[k].add(ti)
  rules={k:next(iter(c)) for k,c in obs.items() if len(c)==1 and len(sup[k])>=MIN_TRACE_SUPPORT}
  return rules,{"keys_with_change":len(obs),"accepted_templates":len(rules)}
def ev(rows,rules):
  m=Counter()
  for row in rows:
    b=world(row["before"],row["action"]); a=world(row["after"],row["action"]); h=len(b); w=len(b[0]) if h else 0; proposals=defaultdict(set)
    for o in comps(b):
      t=rules.get(key(b,o,row["action"]))
      if t is None: continue
      ok=True
      for dr,dc,bv,av in t:
        rr=o["r0"]+dr; cc=o["c0"]+dc
        if not(0<=rr<h and 0<=cc<w and int(b[rr][cc])==bv): ok=False; break
      if not ok: continue
      m["template_firings"]+=1
      for dr,dc,bv,av in t: proposals[(o["r0"]+dr,o["c0"]+dc)].add(int(av))
    pred=[list(map(int,x)) for x in b]
    for (r,c),vals in proposals.items():
      if len(vals)==1: pred[r][c]=next(iter(vals))
    ie=ce=0
    for r in range(h):
      for c in range(w):
        bv=int(b[r][c]); av=int(a[r][c]); pv=int(pred[r][c]); ie+=bv!=av; ce+=pv!=av
        if pv!=bv:
          m["predicted_changes"]+=1
          if pv==av and bv!=av:m["true_changed_correct"]+=1
          elif pv!=av:m["false_changes"]+=1
    m["frames"]+=1;m["identity_errors"]+=ie;m["candidate_errors"]+=ce;m["identity_exact_frames"]+=ie==0;m["candidate_exact_frames"]+=ce==0
  m["pixel_gain"]=m["identity_errors"]-m["candidate_errors"];m["exact_frame_gain"]=m["candidate_exact_frames"]-m["identity_exact_frames"]
  return dict(m)
def main():
  ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--game",required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
  if a.game not in ALLOWED: raise SystemExit("game not allowed")
  ps=sorted(a.input,key=r246.pnum)
  if any(r246.game_id(p)!=a.game for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)):raise SystemExit("exact p0-p4 required")
  traces=[r278.annotated_rows([p]) for p in ps]; total=Counter();folds=[]
  for held in range(5):
    train=[traces[i] for i in range(5) if i!=held];rules,fs=fit(train);x=ev(traces[held],rules);folds.append({"held_trace":held,"fit":fs,"eval":x})
    for k,v in x.items():
      if isinstance(v,int):total[k]+=v
  total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"];total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
  gate=bool(total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0 and total.get("exact_frame_gain",0)>=0)
  verdict="OBJECT_RESIDUAL_ZERO_FALSE_LOTO_SIGNAL" if gate else ("OBJECT_RESIDUAL_GAIN_WITH_FALSE_CHANGE" if total.get("pixel_gain",0)>0 else "NO_SIGNAL")
  out={"schema":"deus/arc3-r324-wa30-ft09-object-residual-loto/1","rung":RUNG,"game":a.game,"protocol":{"data":"p0-p4 only","evaluation":"5-fold LOTO","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},"loto":dict(total),"folds":folds,"gate_pass":gate,"verdict":verdict,"truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
  a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps({"game":a.game,"verdict":verdict,"gate_pass":gate,"loto":out["loto"]},sort_keys=True))
if __name__=="__main__":main()
