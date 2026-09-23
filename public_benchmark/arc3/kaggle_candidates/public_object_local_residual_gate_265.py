#!/usr/bin/env python3
"""R265: source-free object-local residual correction gate for re86.

R264 shows post-transport residuals are 2-3x more concentrated in coordinates
relative to moved-object destinations than in fixed screen coordinates. R265
learns sparse deterministic action-conditioned object-local corrections on top
of the R257 selective transport base.

p0-p4 fit -> p5-p9 per-action ZERO-WRONG selection -> p0-p9 refit -> p10-p19
frozen reused public-development evaluation. Exact visible-state/action lookup
retains precedence. No game source, hidden data, Kaggle runtime/score.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_selective_object_transport_257 as r257

MAX_AREA=13; MIN_FRAC=.8; MIN_SUPPORT=3
MODES=("offset","color_offset","shape_offset")
SUPPORTS=(2,3,5)

def prep(p):
    out=[]
    for i,r in enumerate(r251.prepare_rows([p])):
        x=dict(r); x['transition_id']=f'{p.name}#{i}'; out.append(x)
    return out

def moved(board,model):
    vector,movable=model
    if not vector or not movable:return []
    dr,dc=vector
    return [c for c in r254.components(board) if c['area']<=MAX_AREA and r257.cls(c) in movable and c['r0']+dr>=0 and c['c0']+dc>=0 and c['r1']+dr<len(board) and c['c1']+dc<len(board[0])]

def feature(action,c,do,predv,mode):
    if mode=='offset': return (action,do[0],do[1],predv)
    if mode=='color_offset': return (action,int(c['color']),do[0],do[1],predv)
    if mode=='shape_offset': return (action,int(c['area']),r246.stable(c['shape']),do[0],do[1],predv)
    raise KeyError(mode)

def nearest(comps,rr,cc,dr,dc):
    ranked=[]
    for c in comps:
        r0=c['r0']+dr; c0=c['c0']+dc; cr=(r0+c['r1']+dr)/2; co=(c0+c['c1']+dc)/2
        ranked.append((abs(rr-cr)+abs(cc-co),c,r0,c0))
    ranked.sort(key=lambda x:x[0]); return ranked[0] if ranked else None

def fit_base(rows): return r257.learn(rows,MAX_AREA,MIN_FRAC,MIN_SUPPORT)

def fit_rules(rows,model,mode,support):
    obs=defaultdict(Counter); traces=defaultdict(lambda:defaultdict(set))
    for row in rows:
        base=r257.render(row['before'],model[0],model[1],MAX_AREA)
        comps=moved(row['before'],model)
        if base is None or not comps: continue
        dr,dc=model[0]
        for rr in range(len(base)):
            for cc in range(len(base[0])):
                pv=int(base[rr][cc]); av=int(row['after'][rr][cc])
                if pv==av: continue
                n=nearest(comps,rr,cc,dr,dc)
                if not n: continue
                _,c,r0,c0=n; do=(rr-r0,cc-c0); k=feature(row['action'],c,do,pv,mode)
                obs[k][av]+=1; traces[k][av].add(row['trace'])
    rules={}
    for k,c in obs.items():
        if len(c)!=1: continue
        av=next(iter(c))
        if len(traces[k][av])>=support: rules[k]=int(av)
    return rules

def apply(row,model,rules,mode):
    base=r257.render(row['before'],model[0],model[1],MAX_AREA); comps=moved(row['before'],model)
    if base is None or not comps:return None
    dr,dc=model[0]; proposals=defaultdict(set)
    for c in comps:
        r0=c['r0']+dr; c0=c['c0']+dc
        # scan bounded object-local neighborhood observed by R264; rules themselves fail closed
        for orr in range(-8,13):
            for occ in range(-8,13):
                rr=r0+orr; cc=c0+occ
                if not (0<=rr<len(base) and 0<=cc<len(base[0])): continue
                k=feature(row['action'],c,(orr,occ),int(base[rr][cc]),mode)
                if k in rules: proposals[(rr,cc)].add(rules[k])
    if any(len(v)>1 for v in proposals.values()): return None
    out=[r[:] for r in base]
    for (rr,cc),vs in proposals.items(): out[rr][cc]=next(iter(vs))
    return out

def evaluate(rows,exact,model,rules,mode):
    s=Counter()
    for row in rows:
        s['transitions']+=1
        if row['exact_key'] in exact: s['exact_baseline']+=1; continue
        s['baseline_abstain']+=1; p=apply(row,model,rules,mode)
        if p is None: s['candidate_abstain']+=1; continue
        s['candidate_predictions']+=1; ok=(p==row['after']); s['candidate_correct' if ok else 'candidate_wrong']+=1
    n=s['candidate_predictions']; opp=s['baseline_abstain']
    return {**dict(s),'accuracy':round(s['candidate_correct']/n,6) if n else None,'coverage':round(n/opp,6) if opp else 0.0}

def evaluate_game(paths):
    ps=sorted(paths,key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(20)): raise ValueError('p0..p19 required')
    parts=[prep(p) for p in ps]; tr=[r for x in parts[:5] for r in x]; va=[r for x in parts[5:10] for r in x]; fit=[r for x in parts[:10] for r in x]; ho=[r for x in parts[10:] for r in x]
    tr_by=defaultdict(list); va_by=defaultdict(list); fit_by=defaultdict(list)
    for r in tr: tr_by[r['action']].append(r)
    for r in va: va_by[r['action']].append(r)
    for r in fit: fit_by[r['action']].append(r)
    exact_tr=r251.fit_exact(tr); selected={}; diag={}
    for action in sorted(set(tr_by)|set(va_by)):
        model=fit_base(tr_by[action]); cand={}
        for mode in MODES:
            for sup in SUPPORTS:
                rules=fit_rules(tr_by[action],model,mode,sup); met=evaluate(va_by[action],exact_tr,model,rules,mode); k=f'{mode}_s{sup}'
                cand[k]={'mode':mode,'support':sup,'rule_count':len(rules),'validation':met}
        zero=[k for k,v in cand.items() if v['validation'].get('candidate_predictions',0)>0 and v['validation'].get('candidate_wrong',0)==0 and v['validation'].get('candidate_correct',0)>0]
        if zero:
            zero.sort(key=lambda k:(-cand[k]['validation'].get('candidate_correct',0),-cand[k]['rule_count'],k)); selected[action]=zero[0]
        diag[action]=cand
    exact_fit=r251.fit_exact(fit); refit={}
    for action,k in selected.items():
        v=diag[action][k]; model=fit_base(fit_by[action]); rules=fit_rules(fit_by[action],model,v['mode'],v['support']); refit[action]=(model,rules,v['mode'])
    s=Counter(); by=defaultdict(Counter)
    for row in ho:
        s['transitions']+=1
        if row['exact_key'] in exact_fit: s['exact_baseline']+=1; continue
        s['baseline_abstain']+=1
        if row['action'] not in refit: s['candidate_abstain']+=1; continue
        model,rules,mode=refit[row['action']]; p=apply(row,model,rules,mode)
        if p is None: s['candidate_abstain']+=1; continue
        s['candidate_predictions']+=1; by[row['action']]['predictions']+=1; ok=(p==row['after']); s['candidate_correct' if ok else 'candidate_wrong']+=1; by[row['action']]['correct' if ok else 'wrong']+=1
    n=s['candidate_predictions']; gain=bool(n>0 and s['candidate_wrong']==0 and s['candidate_correct']>0)
    return {'selected_by_action':selected,'selection_diagnostic':diag,'heldout':{**dict(s),'accuracy':round(s['candidate_correct']/n,6) if n else None,'by_action':{a:dict(v) for a,v in by.items()}},'gain':gain}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={g:evaluate_game(ps) for g,ps in sorted(by.items())}; agg=Counter()
    for x in games.values():
        for k in ('transitions','exact_baseline','baseline_abstain','candidate_predictions','candidate_correct','candidate_wrong'): agg[k]+=int(x['heldout'].get(k,0) or 0)
    n=agg['candidate_predictions']; nd=bool(n>0 and agg['candidate_wrong']==0 and agg['candidate_correct']>0)
    out={'schema':'deus/arc3-r265-object-local-residual-gate/1','rung':265,'lineage':{'r264':'run35800237220/artifact10725707268','repair':'sparse object-local residual correction over selective transport'},'protocol':{'select':'p0-p4 fit / p5-p9 per-action zero-wrong','refit':'p0-p9','frozen_eval':'p10-p19','exact_baseline_precedence':True},'games':games,'aggregate':dict(agg),'non_dominated_source_side_gain':nd,'promotion':{'integration_candidate':nd,'solver_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'game_source_read':False,'selection_uses_p0_p9_only':True,'p10_p19_never_updates_selection_or_model':True,'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT','independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'aggregate':dict(agg),'gain':nd,'selected':{g:x['selected_by_action'] for g,x in games.items()}},sort_keys=True))
if __name__=='__main__':main()
