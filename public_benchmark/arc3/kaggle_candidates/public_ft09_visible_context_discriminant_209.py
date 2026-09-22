#!/usr/bin/env python3
"""R209: ft09 exact-mismatch visible-context discriminant search.

Purpose
-------
R208 leaves exactly two public-heldout target-color mismatches. This diagnostic
compares richer PRE-ACTION visible/history feature families while keeping the
R207 mapping protocol fixed: fit deterministic target mappings on p0-p9, freeze,
then audit p10-p19.

This is explicitly iterative public-heldout research. Heldout metrics are used
to compare feature families, so no family selected here is an independent
generalization result or solver/Kaggle promotion.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
import public_ft09_macro_neighbor_rule_207 as r207

RUNG=209
GAME='ft09-0d8bbf25'
CORE=(8,9,12)

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def bucket(n:int)->int:
    if n<=0:return 0
    if n<=1:return 1
    if n<=2:return 2
    if n<=4:return 4
    if n<=8:return 8
    if n<=16:return 16
    if n<=32:return 32
    if n<=64:return 64
    if n<=128:return 128
    if n<=256:return 256
    if n<=512:return 512
    return 1024

def color_hist(board):
    c=Counter(v for row in board for v in row)
    return tuple(sorted((int(v),int(n)) for v,n in c.items()))

def color_tile_hist(board):
    c=Counter(v for row in board for v in row)
    # Separate approximate full 6x6 tile count from residual/HUD pixels.
    return tuple(sorted((int(v),int(n//36),int(n%36)) for v,n in c.items()))

def border_hist(board):
    h,w=len(board),len(board[0])
    vals=[]
    for name,seq in (
        ('T',board[0]),('B',board[-1]),
        ('L',[board[r][0] for r in range(h)]),
        ('R',[board[r][-1] for r in range(h)]),
    ):
        c=Counter(seq)
        vals.append((name,tuple(sorted((int(v),int(n)) for v,n in c.items()))))
    return tuple(vals)

def coarse_activity(board):
    h,w=len(board),len(board[0]); bg=base.dominant_background(board)
    rows=tuple(bucket(sum(v!=bg for v in row)) for row in board)
    cols=tuple(bucket(sum(board[r][c]!=bg for r in range(h))) for c in range(w))
    return (rows,cols)

def feature(name,x):
    cur=x['current'];ctx=x['ctx'];hist=x['history']
    basekey=(cur,ctx['four'],ctx['global_core_counts_bucket'])
    if name=='base':return basekey
    if name=='eight':return basekey+(ctx['eight'],)
    if name=='global_all':return (cur,ctx['four'],x['global_all'])
    if name=='global_tiles':return (cur,ctx['four'],x['global_tiles'])
    if name=='border':return basekey+(x['border'],)
    if name=='activity':return basekey+(x['activity'],)
    if name=='macro_pos':return basekey+(ctx['macro_pos'],)
    if name=='macro_parity':return basekey+(ctx['macro_parity'],)
    if name=='prev_target':return basekey+(hist['prev_target'],)
    if name=='prev_pair':return basekey+(hist['prev_current'],hist['prev_target'])
    if name=='step_bucket':return basekey+(bucket(x['step']),)
    if name=='eight_global_all':return (cur,ctx['eight'],x['global_all'])
    if name=='four_global_tiles_prev':return (cur,ctx['four'],x['global_tiles'],hist['prev_target'])
    if name=='eight_global_tiles_prev':return (cur,ctx['eight'],x['global_tiles'],hist['prev_target'])
    if name=='four_global_tiles_pos':return (cur,ctx['four'],x['global_tiles'],ctx['macro_pos'])
    if name=='four_global_tiles_border':return (cur,ctx['four'],x['global_tiles'],x['border'])
    raise ValueError(name)

FAMILIES=(
 'base','eight','global_all','global_tiles','border','activity',
 'macro_pos','macro_parity','prev_target','prev_pair','step_bucket',
 'eight_global_all','four_global_tiles_prev','eight_global_tiles_prev',
 'four_global_tiles_pos','four_global_tiles_border',
)

def rows(path:Path):
    ev=base.load_events(path);pre=ev[0];step=0
    prev_target=None;prev_current=None
    out=[]
    for e in ev[1:]:
        if e.get('type')!='action':
            pre=e; continue
        before=base.as_grid(pre['board']);after=base.as_grid(e['board'])
        a=base.action_name(e);pre=e;step+=1
        if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':
            continue
        click=c191.parse_mouse(a)
        if click is None:continue
        rr,cc=click;h,w=len(before),len(before[0])
        rr=max(0,min(h-1,rr));cc=max(0,min(w-1,cc))
        bb=r207.comp_bbox(before,rr,cc)
        if bb[4]!=36 or (bb[2]-bb[0]+1,bb[3]-bb[1]+1)!=(6,6):
            continue
        ctx=r207.macro_context(before,bb);cur=ctx['current']
        target=r207.dominant_target(before,after,bb)
        x={
          'trace':path.name,'step':step,'current':cur,'target':target,'ctx':ctx,
          'global_all':color_hist(before),'global_tiles':color_tile_hist(before),
          'border':border_hist(before),'activity':coarse_activity(before),
          'history':{'prev_target':prev_target,'prev_current':prev_current},
        }
        out.append(x)
        prev_current=cur;prev_target=target
    return out

def fit(train,fam):
    obs=defaultdict(Counter)
    for x in train:
        if x['target']==x['current']:continue
        obs[repr(feature(fam,x))][x['target']]+=1
    table={k:next(iter(c)) for k,c in obs.items() if len(c)==1}
    total=sum(sum(c.values()) for c in obs.values())
    det=sum(sum(obs[k].values()) for k in table)
    return table,{
      'values':len(obs),'deterministic_values':len(table),
      'changed_examples':total,'deterministic_examples':det,
      'deterministic_fraction':round(det/total,6) if total else 0.0,
      'conflicted_values':sum(1 for c in obs.values() if len(c)>1),
    }

def evaluate(table,held,fam):
    s=Counter();mistakes=[];correct_examples=[]
    for x in held:
        s['eligible']+=1
        changed=x['target']!=x['current']
        s['actual_changed' if changed else 'actual_identity']+=1
        pred=table.get(repr(feature(fam,x)))
        if pred is None:
            s['abstain']+=1;continue
        s['predictions']+=1
        if changed:s['predicted_on_changed']+=1
        else:s['predicted_on_identity']+=1
        if pred==x['target']:
            s['correct']+=1
            if changed:s['correct_changed']+=1
            if len(correct_examples)<8:
                correct_examples.append({'trace':x['trace'],'step':x['step'],'current':x['current'],'target':x['target'],'pred':pred})
        else:
            s['wrong']+=1
            if len(mistakes)<12:
                mistakes.append({
                  'trace':x['trace'],'step':x['step'],'current':x['current'],
                  'target':x['target'],'pred':pred,'four':list(x['ctx']['four']),
                  'eight':list(x['ctx']['eight']),'global_core':list(x['ctx']['global_core_counts_bucket']),
                  'global_tiles':x['global_tiles'],'macro_pos':list(x['ctx']['macro_pos']),
                  'prev_target':x['history']['prev_target'],
                })
    p=s['predictions'];eligible=s['eligible'];ach=s['actual_changed']
    return {
      **dict(s),
      'accuracy':round(s['correct']/p,6) if p else None,
      'coverage':round(p/eligible,6) if eligible else 0.0,
      'changed_recall':round(s['correct_changed']/ach,6) if ach else None,
      'mistakes':mistakes,'correct_examples':correct_examples,
    }

def run(paths):
    ps=sorted(paths,key=pnum);nums=[pnum(x) for x in ps]
    if nums!=list(range(20)):raise ValueError(f'exact p0..p19 required; got {nums}')
    train=[x for p in ps[:10] for x in rows(p)]
    held=[x for p in ps[10:] for x in rows(p)]
    families={}
    for fam in FAMILIES:
        table,tr=fit(train,fam);ev=evaluate(table,held,fam)
        families[fam]={'train':tr,'heldout':ev}
    # Ranking is diagnostic only and knowingly uses public-heldout metrics.
    def key(item):
        fam,d=item;h=d['heldout']
        return (h.get('wrong',0),-(h.get('correct',0)),-(h.get('coverage',0.0)),fam)
    ranking=[fam for fam,_ in sorted(families.items(),key=key)]
    best=ranking[0]
    return {
      'schema':'deus/arc3-ft09-visible-context-discriminant-search/1',
      'rung':RUNG,'game':GAME,
      'protocol':{
        'fit':'p0-p9 deterministic changed 6x6 MOUSE target mappings',
        'audit':'p10-p19 frozen evaluation per candidate family',
        'selection':'diagnostic ranking only; heldout-informed and NOT promotable',
      },
      'families':families,'diagnostic_ranking':ranking,'diagnostic_best':best,
      'r208_mismatch_targets':[{'trace':'ft09-0d8bbf25_p13_events.jsonl','step':79},{'trace':'ft09-0d8bbf25_p16_events.jsonl','step':49}],
      'promotion':{'solver_promotion':False,'kaggle_packaging':False,'next_gate':'independent_or_cross_trace_stability_gate_required'},
      'truth':{
        'public_trace_only':True,'iterative_public_heldout_research':True,
        'family_search_uses_public_heldout_metrics':True,
        'independent_generalization_claim':False,
        'heldout_never_updates_fitted_tables':True,
        'pre_action_visible_or_observed_history_features_only':True,
        'full_frame_solver_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'rung':RUNG,'diagnostic_best':d['diagnostic_best'],
      'ranking':d['diagnostic_ranking'][:8],
      'summary':{k:{'train':v['train'],'heldout':{x:v['heldout'].get(x) for x in ('predictions','correct','wrong','accuracy','coverage','changed_recall')}} for k,v in d['families'].items()}
    },sort_keys=True))
if __name__=='__main__':main()
