#!/usr/bin/env python3
"""R295: exact mismatch inspection for the R294 sparse local-delta rules.

This rung does not modify the predictor. It freezes the R294 p0-p4 LOTO-gated
3x3 change rules, then inspects every p5-p9 rule firing to localize the single
false change that survived R294. The purpose is falsifier-driven mechanism
selection: capture spatial, 5x5, component and border context for correct vs
wrong firings before choosing the next representation. p10-p19 are forbidden.
"""
from __future__ import annotations

import argparse, hashlib, json
from collections import Counter, defaultdict, deque
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_loto_sparse_local_delta_diag_294 as r294

RUNG=295
TARGET_GAME='lp85-305b61c3'
PAD=-1


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def digest_obj(x):
    return hashlib.sha256(json.dumps(x,separators=(',',':')).encode()).hexdigest()[:16]


def patch5(b,r,c):
    h=len(b); w=len(b[0]) if h else 0; vals=[]
    for dr in range(-2,3):
        row=[]; rr=r+dr
        for dc in range(-2,3):
            cc=c+dc
            row.append(int(b[rr][cc]) if 0<=rr<h and 0<=cc<w else PAD)
        vals.append(row)
    return vals


def same_color_component(b,r,c):
    h=len(b); w=len(b[0]) if h else 0; color=int(b[r][c]); q=deque([(r,c)]); seen={(r,c)}
    while q:
        x,y=q.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<h and 0<=ny<w and (nx,ny) not in seen and int(b[nx][ny])==color:
                seen.add((nx,ny)); q.append((nx,ny))
    rs=[x for x,_ in seen]; cs=[y for _,y in seen]
    return {'color':color,'size':len(seen),'bbox':[min(rs),min(cs),max(rs),max(cs)],'height':max(rs)-min(rs)+1,'width':max(cs)-min(cs)+1}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    train_trace_rows=[r278.annotated_rows([p]) for p in ps[:5]]
    train_rows=[r for tr in train_trace_rows for r in tr]
    rules,gate=r294.build_frozen_rules(train_rows,train_trace_rows)
    firings=[]; grouped=defaultdict(Counter)
    for p in ps[5:]:
        pn=r246.pnum(p); rows=r278.annotated_rows([p])
        for ti,row in enumerate(rows):
            b=world(row['before'],row['action']); aft=world(row['after'],row['action']); h=len(b); w=len(b[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    k=r294.patch_key(b,r,c)
                    if k not in rules: continue
                    pred=int(rules[k]); actual=int(aft[r][c]); before=int(b[r][c]); ok=pred==actual
                    p5=patch5(b,r,c); comp=same_color_component(b,r,c)
                    rec={
                      'trace':pn,'transition_index':ti,'r':r,'c':c,'coarse8':[min(7,(r*8)//max(1,h)),min(7,(c*8)//max(1,w))],
                      'border_distance':min(r,c,h-1-r,w-1-c),'before':before,'pred':pred,'actual':actual,'correct':ok,
                      'rule_digest':digest_obj(k),'patch3':list(k),'patch5_digest':digest_obj(p5),'patch5':p5,
                      'local5_nonbg':sum(int(v)!=r246.bg(b) for row5 in p5 for v in row5 if v!=PAD),
                      'component':comp,
                    }
                    firings.append(rec); grouped[rec['rule_digest']]['correct' if ok else 'wrong']+=1
    wrong=[x for x in firings if not x['correct']]; correct=[x for x in firings if x['correct']]
    out={
      'schema':'deus/arc3-r295-lp85-sparse-rule-mismatch-diagnostic/1','rung':RUNG,'game':TARGET_GAME,
      'frozen_parent':'R294 p0-p4 LOTO-gated sparse 3x3 change rules','fit_gate':gate,
      'protocol':{'rules_fit_and_verified':'p0-p4 only','mismatch_inspection':'p5-p9 only','p10_p19_staged_or_read':False,'predictor_modified':False,'promotion_in_r295':False},
      'summary':{'firings':len(firings),'correct':len(correct),'wrong':len(wrong),'rule_groups':{k:dict(v) for k,v in grouped.items()}},
      'wrong_firings':wrong,'correct_firings':correct,
      'verdict':'MISMATCH_CONTEXT_CAPTURED' if wrong else 'NO_MISMATCH_TO_REPAIR',
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'diagnostic_only':True,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r295':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':out['verdict'],'summary':out['summary'],'wrong_firings':wrong},sort_keys=True))

if __name__=='__main__': main()
