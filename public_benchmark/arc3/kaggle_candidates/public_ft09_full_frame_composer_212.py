#!/usr/bin/env python3
"""R212: ft09 partial full-frame composer from frozen R202 + R211 mechanisms.

Compose only two already-grounded pre-action mechanisms:
  1) R202 conservative identity gate (local|s1, selected on p0-p9 only)
  2) R211 ring2 target-color gate for changed 6x6 MOUSE tiles

For each p10-p19 eligible transition:
  identity gate -> predict unchanged full frame
  else ring2 target -> recolor exactly the clicked 6x6 component
  else abstain

No heldout outcome updates either model. Exact full-board equality is measured.
This is public iterative mechanism research, not hidden generalization or Kaggle.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_macro_neighbor_rule_207 as r207
import public_ft09_mismatch_boarddiff_210 as r210
import public_ft09_ring2_relational_gate_211 as r211

RUNG=212
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def all_rows(path:Path):
    """Match R202 temporal semantics but preserve after/bbox/base/ring2 when eligible."""
    events=base.load_events(path)
    pre=events[0]; prev_action=None; run_len=0; step=0
    out=[]
    for e in events[1:]:
        if e.get('type')!='action':
            pre=e
            continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board'])
        action=base.action_name(e); pre=e
        if not base.same_shape(before,after):
            prev_action=action; run_len=1; step+=1
            continue
        ac=c191.action_class(action)
        if prev_action is not None and c191.action_class(prev_action)==ac:
            run_len+=1
        else:
            run_len=1
        row={
            'path':path.name,'p':pnum(path),'step0':step,
            'before':before,'after':after,'action':action,
            'prev_action':prev_action,'run_len':run_len,'identity':before==after,
            'eligible':False,
        }
        if ac=='MOUSE':
            click=c191.parse_mouse(action)
            if click is not None:
                rr,cc=click; h,w=len(before),len(before[0])
                rr=max(0,min(h-1,rr)); cc=max(0,min(w-1,cc))
                bb=r207.comp_bbox(before,rr,cc)
                if bb[4]==36 and (bb[2]-bb[0]+1,bb[3]-bb[1]+1)==(6,6):
                    ctx=r207.macro_context(before,bb)
                    row.update({
                        'eligible':True,'click':(rr,cc),'bbox':bb,
                        'current':ctx['current'],
                        'target':r207.dominant_target(before,after,bb),
                        'base':(ctx['current'],ctx['four'],ctx['global_core_counts_bucket']),
                        'ring2':r211.ring2(before,bb),
                    })
        out.append(row)
        prev_action=action; step+=1
    return out

def identity_model(paths):
    rs=[]
    for p in paths:
        for r in all_rows(p):
            rs.append({
                'path':r['path'],'before':r['before'],'action':r['action'],
                'prev_action':r['prev_action'],'run_len':r['run_len'],
                'step':r['step0'],'identity':r['identity'],
            })
    # Frozen lineage from R202: local|s1 was selected using p0-p9 only.
    return r202.fit(rs,'local',1)

def ring2_model(paths):
    rs=[r for p in paths for r in r211.rows(p)]
    return r211.fit(rs,lambda r:(r['base'],r['ring2']))[0]

def recolor_bbox(board,bb,target):
    r0,c0,r1,c1,_=bb
    out=[row[:] for row in board]
    for r in range(r0,r1+1):
        for c in range(c0,c1+1):
            out[r][c]=int(target)
    return out

def pack(s):
    p=s['predictions']; e=s['eligible']
    return {
        **dict(s),
        'exact_accuracy':round(s['correct']/p,6) if p else None,
        'coverage':round(p/e,6) if e else 0.0,
    }

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')
    train=ps[:10]; held=ps[10:]
    im=identity_model(train)
    rm=ring2_model(train)
    s=Counter(); branches={'identity':Counter(),'ring2_recolor':Counter()}
    wrong=[]; correct=[]
    for p in held:
        for r in all_rows(p):
            if not r['eligible']:
                continue
            s['eligible']+=1
            idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
            branch=None; pred=None
            if idkey in im:
                branch='identity'
                pred=[row[:] for row in r['before']]
            else:
                tgt=rm.get(repr((r['base'],r['ring2'])))
                if tgt is not None:
                    branch='ring2_recolor'
                    pred=recolor_bbox(r['before'],r['bbox'],tgt)
            if pred is None:
                s['abstain']+=1
                continue
            s['predictions']+=1; branches[branch]['predictions']+=1
            if pred==r['after']:
                s['correct']+=1; branches[branch]['correct']+=1
                if len(correct)<12:
                    correct.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch})
            else:
                s['wrong']+=1; branches[branch]['wrong']+=1
                if len(wrong)<40:
                    resid=r210.diff(pred,r['after'],r['bbox'])
                    wrong.append({
                        'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,
                        'identity_actual':r['identity'],'current':r['current'],'target':r['target'],
                        'structural_residual':resid,
                    })
    metrics=pack(s)
    for k,v in branches.items():
        pp=v['predictions']
        branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    gate=bool(metrics.get('predictions',0)>=100 and metrics.get('exact_accuracy') is not None and metrics['exact_accuracy']>=0.99)
    return {
        'schema':'deus/arc3-ft09-full-frame-composer/1','rung':RUNG,'game':GAME,
        'lineage':{'identity':'R202 local|s1','target_color':'R211 (base,ring2)','recolor':'clicked 6x6 bbox only'},
        'train':{'identity_model_keys':len(im),'ring2_model_keys':len(rm)},
        'heldout':{'all':metrics,'by_branch':branches,'wrong_examples':wrong,'correct_examples':correct},
        'exact_full_frame_gate_pass':gate,
        'promotion':{
            'full_frame_mechanism_gate':gate,
            'solver_promotion':False,
            'kaggle_packaging':False,
            'next_gate':'analyze only structural residual classes from exact-frame failures',
        },
        'truth':{
            'public_trace_only':True,
            'iterative_public_heldout_research':True,
            'heldout_never_updates_models':True,
            'r202_family_frozen_from_p0_p9_selection':True,
            'r211_ring2_frozen_fit_p0_p9':True,
            'full_frame_predictions_measured':True,
            'independent_generalization_claim':False,
            'kaggle_execution':False,
            'submission_quota_spent':False,
            'owner_score_claim':False,
        },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,action='append',default=[])
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    d=run(a.input)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'heldout':d['heldout']['all'],
        'branches':d['heldout']['by_branch'],
        'wrong_count':len(d['heldout']['wrong_examples']),
        'gate':d['exact_full_frame_gate_pass'],
        'promotion':d['promotion'],
    },sort_keys=True))
if __name__=='__main__':
    main()
