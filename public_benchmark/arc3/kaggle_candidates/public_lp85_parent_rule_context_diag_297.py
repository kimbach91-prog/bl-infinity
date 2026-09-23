#!/usr/bin/env python3
"""R297: p0-p4-only hierarchical context diagnostic for lp85.

R296 showed that widening the entire sparse operator from 3x3 to 5x5 explodes
false positives. R297 therefore does not create a new predictor and does not
read p5-p9/p10-p19. It keeps exactly the two verifier-approved R294 parent 3x3
change rules, then asks a narrower mechanism question on p0-p4 only:

  do occurrences of those already-approved parent rules split into repeated,
  deterministic 5x5 child contexts that can act as a hierarchical veto/gate?

This is a representation diagnostic, not threshold tuning or promotion.
"""
from __future__ import annotations

import argparse, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_loto_sparse_local_delta_diag_294 as r294

RUNG=297
TARGET_GAME='lp85-305b61c3'
PAD=-1


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def patch(b,r,c,radius):
    h=len(b); w=len(b[0]) if h else 0; vals=[]
    for dr in range(-radius,radius+1):
        rr=r+dr
        for dc in range(-radius,radius+1):
            cc=c+dc
            vals.append(int(b[rr][cc]) if 0<=rr<h and 0<=cc<w else PAD)
    return tuple(vals)


def digest(k):
    return hashlib.sha256(','.join(map(str,k)).encode()).hexdigest()[:16]


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f'exact p0-p4 required, got {nums}')
    traces=[r278.annotated_rows([p]) for p in ps]
    rows=[r for tr in traces for r in tr]
    parents,gate=r294.build_frozen_rules(rows,traces)
    if len(parents)!=2: raise SystemExit(f'expected 2 R294 parent rules, got {len(parents)}')

    ctx=defaultdict(lambda: defaultdict(Counter))
    support=defaultdict(lambda: defaultdict(set))
    parent_counts=Counter()
    transition_id=0
    for ti,tr in enumerate(traces):
        for ri,row in enumerate(tr):
            b=world(row['before'],row['action']); after=world(row['after'],row['action'])
            h=len(b); w=len(b[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    p3=patch(b,r,c,1)
                    if p3 not in parents: continue
                    p5=patch(b,r,c,2); actual=int(after[r][c])
                    pd=digest(p3); cd=digest(p5)
                    ctx[pd][cd][actual]+=1
                    support[pd][cd].add((ti,ri))
                    parent_counts[pd]+=1
            transition_id+=1

    parent_summaries={}
    totals=Counter()
    for p3,pred in parents.items():
        pd=digest(p3); children=[]
        for cd,out in sorted(ctx[pd].items()):
            sup=len(support[pd][cd]); deterministic=len(out)==1; only=next(iter(out)) if deterministic else None
            stable_change=deterministic and only==int(pred) and int(pred)!=int(p3[len(p3)//2]) and sup>=2
            children.append({'child5_digest':cd,'outcomes':dict(out),'distinct_transitions':sup,'deterministic':deterministic,'matches_parent_prediction':bool(deterministic and only==int(pred)),'stable_change_child':bool(stable_change)})
            totals['children']+=1; totals['deterministic_children']+=deterministic; totals['supported2_children']+=sup>=2; totals['stable_change_children']+=stable_change
        parent_summaries[pd]={'parent_prediction':int(pred),'parent_center':int(p3[len(p3)//2]),'occurrences':int(parent_counts[pd]),'child_contexts':children}

    stable_occ=sum(sum(sum(ch['outcomes'].values()) for ch in p['child_contexts'] if ch['stable_change_child']) for p in parent_summaries.values())
    out={
      'schema':'deus/arc3-r297-lp85-parent-rule-context/1','rung':RUNG,'game':TARGET_GAME,
      'lineage':{'r294':'two verifier-approved 3x3 change parent rules','r295':'one parent rule has five correct and one wrong p5-p9 firing with differing 5x5 context','r296':'global 5x5 operator rejected because 783 false changes and -9 exact frames'},
      'protocol':{'diagnostic':'p0-p4 only','p5_p9_staged_or_read':False,'p10_p19_staged_or_read':False,'predictor_modified':False,'threshold_sweep':False},
      'r294_parent_gate':gate,
      'summary':{'parent_rules':len(parents),'parent_occurrences':sum(parent_counts.values()),'child_contexts':totals['children'],'deterministic_child_contexts':totals['deterministic_children'],'support_ge2_child_contexts':totals['supported2_children'],'stable_change_child_contexts':totals['stable_change_children'],'stable_change_child_occurrences':stable_occ},
      'parents':parent_summaries,
      'verdict':'HIERARCHICAL_CHILD_CONTEXT_SIGNAL' if totals['stable_change_children']>0 else 'NO_HIERARCHICAL_CHILD_CONTEXT_SIGNAL',
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p5_p9_read':False,'p10_p19_read':False,'representation_diagnostic_only':True,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r297':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':out['verdict'],'summary':out['summary'],'parent_digests':sorted(parent_summaries)},sort_keys=True))

if __name__=='__main__': main()
