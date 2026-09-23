#!/usr/bin/env python3
"""R299: p0-p4-only seeded structural residual diagnostic for lp85.

R298 produces ten zero-false positive seed pixels on p5-p9 but no exact-frame
gain. R299 asks the next discriminating question without reading validation:
when an accepted hierarchical seed fires on p0-p4, is the actual before->after
residual component containing that seed a repeated normalized structure?
A repeated component would justify an object/residual expansion representation;
otherwise the next repair should move to temporal/phase state rather than grow
local spatial templates.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter, defaultdict, deque
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_hierarchical_sparse_delta_gate_298 as r298

TARGET_GAME='lp85-305b61c3'; RUNG=299

def world(board,action): return r275.canon_board(board,action,use_ui_mask=True)
def dg(obj): return hashlib.sha256(json.dumps(obj,separators=(',',':')).encode()).hexdigest()[:16]

def component(mask,sr,sc):
    h=len(mask); w=len(mask[0]) if h else 0
    if not (0<=sr<h and 0<=sc<w and mask[sr][sc]): return []
    q=deque([(sr,sc)]); seen={(sr,sc)}
    while q:
        r,c=q.popleft()
        for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
            rr,cc=r+dr,c+dc
            if 0<=rr<h and 0<=cc<w and mask[rr][cc] and (rr,cc) not in seen:
                seen.add((rr,cc)); q.append((rr,cc))
    return sorted(seen)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f'exact p0-p4 required, got {nums}')
    traces=[r278.annotated_rows([p]) for p in ps]; train=[r for t in traces for r in t]
    rules,fit=r298.fit_hierarchy(train,traces)
    occurrences=[]; sig_counts=Counter(); by_rule=defaultdict(Counter)
    for ti,tr in enumerate(traces):
        for ri,row in enumerate(tr):
            b=world(row['before'],row['action']); aft=world(row['after'],row['action']); h=len(b); w=len(b[0]) if h else 0
            mask=[[int(b[r][c])!=int(aft[r][c]) for c in range(w)] for r in range(h)]
            for r in range(h):
                for c in range(w):
                    key=(r298.patch(b,r,c,1),r298.patch(b,r,c,2))
                    if key not in rules: continue
                    comp=component(mask,r,c)
                    if not comp: continue
                    rel=sorted((rr-r,cc-c,int(b[rr][cc]),int(aft[rr][cc])) for rr,cc in comp)
                    sig=dg(rel); rk=dg([list(key[0]),list(key[1])])
                    sig_counts[sig]+=1; by_rule[rk][sig]+=1
                    rs=[x[0] for x in comp]; cs=[x[1] for x in comp]
                    occurrences.append({'trace':ti,'transition':ri,'seed':[r,c],'rule_digest':rk,'component_size':len(comp),'bbox':[min(rs),min(cs),max(rs),max(cs)],'signature':sig,'relative_residual':rel if len(rel)<=64 else None})
    repeated={k:v for k,v in sig_counts.items() if v>=2}; stable_rules={rk:dict(cnt) for rk,cnt in by_rule.items() if max(cnt.values(),default=0)>=2}
    sizes=Counter(o['component_size'] for o in occurrences)
    verdict='SEEDED_STRUCTURAL_RESIDUAL_SIGNAL' if repeated else 'NO_SEEDED_STRUCTURAL_RESIDUAL_SIGNAL'
    out={'schema':'deus/arc3-r299-lp85-seeded-structural-residual/1','rung':RUNG,'game':TARGET_GAME,
         'protocol':{'diagnostic':'p0-p4 only','p5_p9_staged_or_read':False,'p10_p19_staged_or_read':False,'predictor_modified':False},
         'fit_gate':fit,'summary':{'seed_occurrences':len(occurrences),'distinct_residual_signatures':len(sig_counts),'repeated_residual_signatures':repeated,'component_size_histogram':dict(sizes),'rule_groups_with_repeated_residual':stable_rules},
         'occurrences':occurrences,'verdict':verdict,
         'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p5_p9_read':False,'p10_p19_read':False,'diagnostic_only':True,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'summary':out['summary']},sort_keys=True))
if __name__=='__main__': main()
