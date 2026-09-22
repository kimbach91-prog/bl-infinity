#!/usr/bin/env python3
"""R209: exact discriminant diagnostic for the two R208 frozen ft09 mismatches.

R208 froze the R207 current+N/E/S/W+global-core selector and obtained 371/373
correct target-color predictions on p10-p19. This diagnostic does not broaden
search arbitrarily: it reproduces that frozen base selector, identifies only its
heldout mistakes, and tests a small pre-registered set of pre-action/history
features that could discriminate phase/HUD/goal-precedence state. p10-p19 never
updates any table. This is iterative public-heldout research, not independent
generalization and not a full-frame solver.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
import public_ft09_macro_neighbor_rule_207 as r207

RUNG=209
GAME='ft09-0d8bbf25'
PALETTE=(0,2,4,5,8,9,11,12)

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def hist_rows(board,start):
    c=Counter(v for row in board[start:] for v in row)
    return tuple(c[k] for k in PALETTE)

def full_hist(board):
    c=Counter(v for row in board for v in row)
    return tuple(c[k] for k in PALETTE)

def sig(board):
    raw=json.dumps(board,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()[:16]

def records(path:Path):
    ev=base.load_events(path); pre=ev[0]; step=0; prev_target=None; prev_changed=False
    for e in ev[1:]:
        if e.get('type')!='action':
            pre=e; continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board']); a=base.action_name(e)
        pre=e; step+=1
        if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':
            prev_target=None; prev_changed=False; continue
        click=c191.parse_mouse(a)
        if click is None:
            prev_target=None; prev_changed=False; continue
        rr,cc=click; h,w=len(before),len(before[0]); rr=max(0,min(h-1,rr)); cc=max(0,min(w-1,cc))
        bb=r207.comp_bbox(before,rr,cc)
        if bb[4]!=36 or (bb[2]-bb[0]+1,bb[3]-bb[1]+1)!=(6,6):
            prev_target=None; prev_changed=False; continue
        ctx=r207.macro_context(before,bb); cur=ctx['current']; target=r207.dominant_target(before,after,bb)
        basekey=(cur,ctx['four'],ctx['global_core_counts_bucket'])
        feats={
          'eight':ctx['eight'],
          'macro_pos':ctx['macro_pos'],
          'macro_parity':ctx['macro_parity'],
          'prev_target':prev_target,
          'prev_changed':prev_changed,
          'bottom4_hist':hist_rows(before,max(0,h-4)),
          'bottom8_hist':hist_rows(before,max(0,h-8)),
          'full_hist':full_hist(before),
          'clicked_row_band':bb[0]//8,
          'clicked_col_band':bb[1]//8,
        }
        yield {'trace':path.name,'p':pnum(path),'step':step,'current':cur,'target':target,
               'changed':target!=cur,'base':basekey,'features':feats,'board_sig':sig(before),
               'four':ctx['four'],'eight':ctx['eight'],'global':ctx['global_core_counts_bucket'],
               'macro_pos':ctx['macro_pos']}
        prev_target=target; prev_changed=(target!=cur)

def det_table(rows,keyfn):
    obs=defaultdict(Counter)
    for r in rows:
        if r['changed']:
            obs[repr(keyfn(r))][r['target']]+=1
    table={k:next(iter(c)) for k,c in obs.items() if len(c)==1}
    return table,obs

def evaluate(rows,table,keyfn):
    s=Counter(); mistakes=[]
    for r in rows:
        s['eligible']+=1
        k=repr(keyfn(r)); pred=table.get(k)
        if pred is None:
            s['abstain']+=1; continue
        s['predictions']+=1
        if pred==r['target']: s['correct']+=1
        else:
            s['wrong']+=1
            if len(mistakes)<10: mistakes.append({**r,'pred':pred})
    p=s['predictions']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
            'coverage':round(p/s['eligible'],6) if s['eligible'] else 0.0},mistakes

def compact(r):
    return {'trace':r['trace'],'p':r['p'],'step':r['step'],'current':r['current'],'target':r['target'],
            'changed':r['changed'],'four':list(r['four']),'eight':list(r['eight']),
            'global':list(r['global']),'macro_pos':list(r['macro_pos']),
            'features':{k:(list(v) if isinstance(v,tuple) else v) for k,v in r['features'].items()},
            'board_sig':r['board_sig']}

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    train=[r for p in ps[:10] for r in records(p)]
    held=[r for p in ps[10:] for r in records(p)]
    basefn=lambda r:r['base']
    bt,bobs=det_table(train,basefn); bmet,bmist=evaluate(held,bt,basefn)

    feature_names=['eight','macro_pos','macro_parity','prev_target','prev_changed','bottom4_hist','bottom8_hist','full_hist','clicked_row_band','clicked_col_band']
    variants={}
    for f in feature_names:
        fn=lambda r,f=f:(r['base'],r['features'][f])
        tab,obs=det_table(train,fn); met,mist=evaluate(held,tab,fn)
        variants[f]={'metrics':met,'train_values':len(obs),'train_deterministic_values':len(tab),
                     'mistake_count':len(mist),'mistakes':[compact(x) | {'pred':x['pred']} for x in mist]}

    mismatch_keys={repr(r['base']) for r in bmist}
    mismatch_context=[]
    for k in sorted(mismatch_keys):
        tr=[compact(r) for r in train if repr(r['base'])==k]
        he=[compact(r) | ({'pred':bt[k]} if k in bt else {}) for r in held if repr(r['base'])==k]
        mismatch_context.append({'base_key':k,'train_target_counts':dict(bobs[k]),'train_examples':tr,'heldout_examples':he})

    zero_wrong=[]
    for f,v in variants.items():
        m=v['metrics']
        if m.get('predictions',0)>0 and m.get('wrong',0)==0:
            zero_wrong.append({'feature':f,**m})
    zero_wrong.sort(key=lambda x:(-x.get('predictions',0),x['feature']))

    return {
      'schema':'deus/arc3-ft09-relational-mismatch-discriminant/1','rung':RUNG,'game':GAME,
      'scope':'R208_exact_two-mismatch_discriminant_only',
      'base_heldout':bmet,'base_mistakes':[compact(x) | {'pred':x['pred']} for x in bmist],
      'variants':variants,'zero_wrong_variants':zero_wrong,'mismatch_context':mismatch_context,
      'verdict':{'base_reproduced':bmet.get('correct')==371 and bmet.get('wrong')==2,
                 'discriminant_found':bool(zero_wrong),
                 'solver_promotion':False,'kaggle_packaging':False},
      'truth':{'public_trace_only':True,'iterative_public_heldout_research':True,
               'heldout_never_updates_model':True,'independent_generalization_claim':False,
               'diagnostic_only':True,'full_frame_solver_claim':False,'kaggle_execution':False,
               'submission_quota_spent':False,'owner_score_claim':False}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); d=run(a.input); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'base':d['base_heldout'],'zero_wrong':d['zero_wrong_variants'],'verdict':d['verdict']},sort_keys=True))
if __name__=='__main__': main()
