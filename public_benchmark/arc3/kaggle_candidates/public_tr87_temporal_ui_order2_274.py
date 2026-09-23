#!/usr/bin/env python3
"""R274: tr87 temporal UI order-2 falsifier.

R273T showed first-order UI factorization selected cleanly on p5-p9 for tr87
but failed frozen p10-p19 (6 correct / 7 wrong). This tests one discriminating
mechanism only: whether the UI residual is second-order in the immediately
previous action. The gameplay-core factorization and static UI mask are unchanged.

Protocol: p0-p4 fit -> p5-p9 zero-wrong selection -> p0-p9 refit -> p10-p19
frozen evaluation. PUBLIC_OFFLINE only; no hidden/Kaggle score or submission.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268

MIN_SUPPORT=2

def prepare(path:Path):
    ev=r246.load_events(path); pre=ev[0]; prev_action='<START>'; out=[]
    for e in ev[1:]:
        if e.get('type')!='action': pre=e; continue
        b=[[int(v) for v in row] for row in pre['board']]
        a=[[int(v) for v in row] for row in e['board']]
        if b and a and len(b)==len(a) and len(b[0])==len(a[0]):
            act=r246.action_name(e)
            out.append({'trace':path.name,'before':b,'after':a,'action':act,'prev_action':prev_action,
                        'exact_key':r246.digest({'b':b,'a':act}),'after_digest':r246.digest(a)})
            prev_action=act
        pre=e
    return out

def pos(h,w): return [(r,c) for r in range(h) for c in range(w) if c==0 or c==w-1 or r in {0,1,h-1}]
def uivals(b): return tuple(int(b[r][c]) for r,c in pos(len(b),len(b[0])))
def core(b): return r268.masked(b)
def cd(b): return r246.digest(core(b))
def ud(b): return r246.digest(uivals(b))

def fit_exact(rs):
    obs=defaultdict(Counter); fr={}
    for r in rs: obs[r['exact_key']][r['after_digest']]+=1; fr[(r['exact_key'],r['after_digest'])]=r['after']
    out={}
    for k,c in obs.items():
        if len(c)==1:
            d=next(iter(c)); out[k]=fr[(k,d)]
    return out

def fit(rs,order2:bool):
    co=defaultdict(Counter); cf={}; uo=defaultdict(Counter); uf={}; sup=defaultdict(set)
    for r in rs:
        ck=(cd(r['before']),r['action']); ca=core(r['after']); cad=r246.digest(ca)
        co[ck][cad]+=1; cf[(ck,cad)]=ca
        uk=(ud(r['before']),r['action'],r['prev_action']) if order2 else (ud(r['before']),r['action'])
        ua=uivals(r['after']); uad=r246.digest(ua)
        uo[uk][uad]+=1; uf[(uk,uad)]=ua; sup[uk].add(cd(r['before']))
    ct={k:cf[(k,next(iter(c)))] for k,c in co.items() if len(c)==1}
    ut={}; amb=low=0
    for k,c in uo.items():
        if len(c)!=1: amb+=1; continue
        if len(sup[k])<MIN_SUPPORT: low+=1; continue
        d=next(iter(c)); ut[k]=uf[(k,d)]
    return ct,ut,{'core_keys':len(ct),'ui_keys':len(ut),'ui_ambiguous':amb,'ui_low_support':low}

def compose(ca,ua):
    o=[row[:] for row in ca]; pp=pos(len(o),len(o[0]))
    if len(pp)!=len(ua): return None
    for (r,c),v in zip(pp,ua): o[r][c]=int(v)
    return o

def eval_added(rs,ex,ct,ut,order2):
    s=Counter(); exs=[]
    for r in rs:
        s['transitions']+=1
        if r['exact_key'] in ex: s['baseline_predictions']+=1; continue
        s['baseline_abstain']+=1
        ck=(cd(r['before']),r['action'])
        uk=(ud(r['before']),r['action'],r['prev_action']) if order2 else (ud(r['before']),r['action'])
        ca=ct.get(ck); ua=ut.get(uk)
        if ca is None or ua is None: s['candidate_abstain']+=1; continue
        pr=compose(ca,ua)
        if pr is None: s['candidate_abstain']+=1; continue
        s['candidate_predictions']+=1; ok=pr==r['after']; s['candidate_correct' if ok else 'candidate_wrong']+=1
        if len(exs)<20: exs.append({'trace':r['trace'],'action':r['action'],'prev_action':r['prev_action'],'correct':ok})
    p=s['candidate_predictions']; opp=s['baseline_abstain']
    return {**dict(s),'accuracy':round(s['candidate_correct']/p,6) if p else None,
            'coverage':round(p/opp,6) if opp else 0.0,'examples':exs}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); assert [r246.pnum(p) for p in ps]==list(range(20))
    parts=[prepare(p) for p in ps]; tr=sum(parts[:5],[]); va=sum(parts[5:10],[]); fitrs=sum(parts[:10],[]); ho=sum(parts[10:],[])
    ex0=fit_exact(tr)
    c1,u1,d1=fit(tr,False); v1=eval_added(va,ex0,c1,u1,False)
    c2,u2,d2=fit(tr,True); v2=eval_added(va,ex0,c2,u2,True)
    selected=bool(v2.get('candidate_predictions',0)>0 and v2.get('candidate_wrong',0)==0)
    ex=fit_exact(fitrs); c2r,u2r,d2r=fit(fitrs,True)
    held=eval_added(ho,ex,c2r,u2r,True) if selected else {'transitions':len(ho),'candidate_predictions':0,'candidate_correct':0,'candidate_wrong':0,'accuracy':None,'coverage':0.0}
    promote=bool(selected and held.get('candidate_predictions',0)>0 and held.get('candidate_wrong',0)==0)
    out={'schema':'deus/arc3-r274-tr87-temporal-ui-order2/1','game':'tr87-cd924810',
         'hypothesis':'UI residual may require previous-action temporal state; all other representation pieces unchanged',
         'selection':{'order1_reference':v1,'order2':v2,'order1_fit':d1,'order2_fit':d2,'selected_order2':selected},
         'refit_order2':d2r,'heldout_p10_p19':held,'promote_representation':promote,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_updates_model':False,'kaggle_execution':False,'competition_submission':False,'quota_spent':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'selection_order1':v1,'selection_order2':v2,'heldout_order2':held,'promote':promote},sort_keys=True))
if __name__=='__main__': main()
