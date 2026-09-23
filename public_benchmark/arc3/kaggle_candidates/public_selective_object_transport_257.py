#!/usr/bin/env python3
"""R257: source-free selective object-transport gate for re86."""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_object_motion_diag_256 as r256
RUNG=257
VARIANTS=((1,0.80,3),(1,0.90,3),(1,1.00,3),(13,0.80,3),(13,0.90,3),(13,1.00,3),(36,0.80,3),(36,0.90,3),(36,1.00,3),(36,0.90,5))
def cls(comp): return (int(comp['color']), int(comp['area']), r246.stable(comp['shape']))
def prepare(paths):
    out=[]
    for p in paths:
        for step,row in enumerate(r251.prepare_rows([p])):
            x=dict(row); x['transition_id']=f"{p.name}#{step}"; out.append(x)
    return out
def learn(rows,max_area:int,min_frac:float,min_support:int):
    vec=Counter(); per=defaultdict(Counter)
    for row in rows:
        matches,_,_=r256.match_components(row['before'],row['after'])
        for b,a in matches:
            if b['area']>max_area: continue
            d=(a['r0']-b['r0'],a['c0']-b['c0']); per[cls(b)][d]+=1
            if d!=(0,0): vec[d]+=1
    if not vec: return None,{}
    dominant=vec.most_common(1)[0][0]; movable={}
    for k,c in per.items():
        support=sum(c.values()); frac=c[dominant]/support if support else 0.0
        if support>=min_support and frac>=min_frac and dominant!=(0,0): movable[k]=support
    return dominant,movable
def render(board,vector,movable,max_area:int):
    if not vector or not movable: return None
    comps=[c for c in r254.components(board) if c['area']<=max_area and cls(c) in movable]
    if not comps: return None
    h=len(board); w=len(board[0]); bg=r246.bg(board); dr,dc=vector
    for c in comps:
        if c['r0']+dr<0 or c['c0']+dc<0 or c['r1']+dr>=h or c['c1']+dc>=w: return None
    out=[list(map(int,row)) for row in board]
    for c in comps:
        for rr,cc in c['shape']: out[c['r0']+rr][c['c0']+cc]=int(bg)
    for c in comps:
        for rr,cc in c['shape']: out[c['r0']+rr+dr][c['c0']+cc+dc]=int(c['color'])
    return out
def eval_rows(rows,exact,model,max_area):
    s=Counter(); examples=[]; vector,movable=model
    for row in rows:
        s['transitions']+=1
        if row['exact_key'] in exact: s['exact_baseline']+=1; continue
        s['baseline_abstain']+=1; p=render(row['before'],vector,movable,max_area)
        if p is None: s['candidate_abstain']+=1; continue
        s['candidate_predictions']+=1; ok=(p==row['after']); s['candidate_correct' if ok else 'candidate_wrong']+=1
        if len(examples)<20: examples.append({'trace':row['trace'],'action':row['action'],'correct':ok,'vector':list(vector) if vector else None})
    n=s['candidate_predictions']; opp=s['baseline_abstain']
    return {**dict(s),'accuracy':round(s['candidate_correct']/n,6) if n else None,'coverage_of_baseline_abstain':round(n/opp,6) if opp else 0.0,'examples':examples}
def evaluate_game(paths):
    ps=sorted(paths,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise ValueError(f'exact p0..p19 required, got {nums}')
    parts=[prepare([p]) for p in ps]; tr=[r for x in parts[:5] for r in x]; va=[r for x in parts[5:10] for r in x]; fit=[r for x in parts[:10] for r in x]; ho=[r for x in parts[10:] for r in x]
    tr_by=defaultdict(list); va_by=defaultdict(list); fit_by=defaultdict(list)
    for r in tr: tr_by[r['action']].append(r)
    for r in va: va_by[r['action']].append(r)
    for r in fit: fit_by[r['action']].append(r)
    exact_tr=r251.fit_exact(tr); selected={}; diag={}
    for action in sorted(set(tr_by)|set(va_by)):
        cand={}
        for max_area,min_frac,min_support in VARIANTS:
            model=learn(tr_by[action],max_area,min_frac,min_support); met=eval_rows(va_by[action],exact_tr,model,max_area); key=f'a{max_area}_f{int(min_frac*100)}_s{min_support}'
            cand[key]={'max_area':max_area,'min_frac':min_frac,'min_support':min_support,'vector':list(model[0]) if model[0] else None,'movable_class_count':len(model[1]),'validation':met}
        zero=[k for k,v in cand.items() if v['validation'].get('candidate_predictions',0)>0 and v['validation'].get('candidate_wrong',0)==0]
        if zero:
            zero.sort(key=lambda k:(-cand[k]['validation'].get('candidate_correct',0),-cand[k]['validation'].get('candidate_predictions',0),k)); selected[action]=zero[0]
        diag[action]=cand
    exact_fit=r251.fit_exact(fit); refit={}
    for action,k in selected.items():
        v=diag[action][k]; refit[action]=(v['max_area'],learn(fit_by[action],v['max_area'],v['min_frac'],v['min_support']))
    s=Counter(); by_action=defaultdict(Counter); examples=[]
    for row in ho:
        s['transitions']+=1
        if row['exact_key'] in exact_fit: s['exact_baseline']+=1; continue
        s['baseline_abstain']+=1
        if row['action'] not in refit: s['candidate_abstain']+=1; continue
        max_area,model=refit[row['action']]; p=render(row['before'],model[0],model[1],max_area)
        if p is None: s['candidate_abstain']+=1; continue
        s['candidate_predictions']+=1; by_action[row['action']]['predictions']+=1; ok=(p==row['after']); s['candidate_correct' if ok else 'candidate_wrong']+=1; by_action[row['action']]['correct' if ok else 'wrong']+=1
        if len(examples)<30: examples.append({'trace':row['trace'],'action':row['action'],'variant':selected[row['action']],'vector':list(model[0]) if model[0] else None,'correct':ok})
    n=s['candidate_predictions']; opp=s['baseline_abstain']; held={**dict(s),'accuracy':round(s['candidate_correct']/n,6) if n else None,'coverage_of_baseline_abstain':round(n/opp,6) if opp else 0.0,'by_action':{a:dict(v) for a,v in by_action.items()},'examples':examples}; gain=bool(n>0 and s['candidate_wrong']==0 and s['candidate_correct']>0)
    return {'selected_by_action':selected,'selection_diagnostic':diag,'heldout':held,'gain':gain}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={g:evaluate_game(ps) for g,ps in sorted(by.items())}; agg=Counter(); gains=[]
    for g,x in games.items():
        h=x['heldout']
        for k in ('transitions','exact_baseline','baseline_abstain','candidate_predictions','candidate_correct','candidate_wrong'): agg[k]+=int(h.get(k,0) or 0)
        if x['gain']: gains.append(g)
    n=agg['candidate_predictions']; opp=agg['baseline_abstain']; aggregate={**dict(agg),'candidate_accuracy':round(agg['candidate_correct']/n,6) if n else None,'candidate_coverage_of_baseline_abstain':round(n/opp,6) if opp else 0.0,'gain_games':gains,'gain_game_count':len(gains),'game_count':len(games)}; nd=bool(n>0 and agg['candidate_wrong']==0 and agg['candidate_correct']>0)
    out={'schema':'deus/arc3-r257-selective-object-transport/1','rung':RUNG,'games':games,'aggregate':aggregate,'non_dominated_source_side_gain':nd,'promotion':{'integration_candidate':nd,'solver_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'game_source_read':False,'selection_uses_p0_p9_only':True,'p10_p19_never_updates_selection_or_model':True,'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT','independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'aggregate':aggregate,'gain':nd,'selected':{g:x['selected_by_action'] for g,x in games.items()}},sort_keys=True))
if __name__=='__main__': main()
