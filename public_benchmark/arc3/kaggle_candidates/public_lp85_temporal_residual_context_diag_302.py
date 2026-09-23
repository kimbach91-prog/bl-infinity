#!/usr/bin/env python3
"""R302: collision-aware causal temporal residual diagnostic for lp85.

R301 proved that residual recurrence carries substantial signal but also creates
many false changes.  This rung changes the representation rather than tuning a
threshold: residual histories are keyed by causal context available before the
current action (action class, past-only phase, anchor-local pre-state patch,
or coarse anchor region).  Only p0-p4 are staged/read.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_seeded_structural_residual_gate_300 as r300
import public_lp85_temporal_residual_motion_diag_301 as r301

TARGET_GAME='lp85-305b61c3'
RUNG=302
CTX_MODES=(
    'ACTION',
    'PHASE',
    'LOCAL3',
    'ACTION_LOCAL3',
    'ACTION_REGION4',
    'PHASE_LOCAL3',
)
HISTORY_MODES=('H2_PERIOD_VELOCITY','H3_STABLE_PERIOD_VELOCITY')


def patch(board,r,c,rad=1):
    h=len(board); w=len(board[0]) if h else 0
    return tuple(
        int(board[rr][cc]) if 0<=rr<h and 0<=cc<w else -1
        for rr in range(r-rad,r+rad+1)
        for cc in range(c-rad,c+rad+1)
    )


def static_ctx(row, base, anchor, mode):
    r,c=anchor; h=len(base); w=len(base[0]) if h else 0
    action=r275.action_class(row['action'])
    phase=tuple(row.get('phase_before',('NA',0)))
    local=patch(base,r,c,1)
    region=(min(3,(4*r)//max(1,h)),min(3,(4*c)//max(1,w)))
    if mode=='ACTION': return ('A',action)
    if mode=='PHASE': return ('P',phase)
    if mode=='LOCAL3': return ('L',local)
    if mode=='ACTION_LOCAL3': return ('AL',action,local)
    if mode=='ACTION_REGION4': return ('AR',action,region)
    if mode=='PHASE_LOCAL3': return ('PL',phase,local)
    raise KeyError(mode)


def current_ctx_matches(stored_ctx,row,base,anchor,mode):
    return static_ctx(row,base,anchor,mode)==stored_ctx


def run_mode(traces,templates,ctx_mode,hist_mode):
    total=Counter(); per_trace={}
    for ti,trace in enumerate(traces):
        histories=defaultdict(list)
        tm=Counter()
        for idx,row in enumerate(trace):
            b,actual,base=r301.r300_predict(row,templates)
            h=len(base); w=len(base[0]) if h else 0
            proposals=defaultdict(set); fires=0
            for (res_sig,ctx),hist in histories.items():
                anchor=r301.due_prediction(hist,idx,hist_mode)
                if anchor is None: continue
                r0,c0=anchor
                if not (0<=r0<h and 0<=c0<w): continue
                if not current_ctx_matches(ctx,row,base,anchor,ctx_mode):
                    continue
                ok=True
                for dr,dc,before,after in res_sig:
                    rr,cc=r0+dr,c0+dc
                    if not (0<=rr<h and 0<=cc<w and int(base[rr][cc])==int(before)):
                        ok=False; break
                if not ok: continue
                fires+=1
                for dr,dc,before,after in res_sig:
                    proposals[(r0+dr,c0+dc)].add(int(after))
            cand=[x[:] for x in base]
            for (r,c),vals in proposals.items():
                if len(vals)==1: cand[r][c]=next(iter(vals))
                else: tm['conflicting_cells']+=1
            base_err=cand_err=0
            for r in range(h):
                for c in range(w):
                    bv,cv,av=int(base[r][c]),int(cand[r][c]),int(actual[r][c])
                    base_err += bv!=av; cand_err += cv!=av
                    if cv!=bv:
                        tm['predicted_changes']+=1
                        if cv==av and bv!=av: tm['true_changed_correct']+=1
                        elif cv!=av: tm['false_changes']+=1
            tm['frames']+=1; tm['base_errors']+=base_err; tm['candidate_errors']+=cand_err
            tm['base_exact_frames']+=base_err==0; tm['candidate_exact_frames']+=cand_err==0
            tm['temporal_firings']+=fires

            comps=r301.residual_components(base,actual)
            grouped=defaultdict(list)
            for comp in comps:
                ctx=static_ctx(row,base,comp['anchor'],ctx_mode)
                grouped[(comp['rel'],ctx)].append(comp)
            for key,same in grouped.items():
                if len(same)==1:
                    histories[key].append((idx,same[0]['anchor']))
                else:
                    tm['ambiguous_same_context_rows']+=1
        tm['error_reduction_vs_r300_base']=tm['base_errors']-tm['candidate_errors']
        tm['exact_frame_delta_vs_r300_base']=tm['candidate_exact_frames']-tm['base_exact_frames']
        per_trace[str(ti)]=dict(tm); total.update(tm)
    # Counter.update would sum derived metrics correctly because per-trace metrics are additive.
    return dict(total),per_trace


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f'exact p0-p4 required, got {nums}')
    traces=[r278.annotated_rows([p]) for p in ps]
    train=[r for tr in traces for r in tr]
    templates,fit=r300.fit_templates(train,traces)
    modes={}
    for ctx in CTX_MODES:
        for hist in HISTORY_MODES:
            name=f'{ctx}__{hist}'
            total,per=run_mode(traces,templates,ctx,hist)
            modes[name]={'context':ctx,'history':hist,'total':total,'per_trace':per}
    safe=[]
    for name,v in modes.items():
        t=v['total']
        if int(t.get('predicted_changes',0))>0 and int(t.get('false_changes',0))==0 and int(t.get('error_reduction_vs_r300_base',0))>0:
            safe.append(name)
    best=max(safe,key=lambda n:(modes[n]['total']['error_reduction_vs_r300_base'],modes[n]['total'].get('predicted_changes',0))) if safe else None
    best_any=max(modes,key=lambda n:(modes[n]['total'].get('error_reduction_vs_r300_base',0),-modes[n]['total'].get('false_changes',0)))
    if best: verdict='CONTEXT_TEMPORAL_ZERO_FALSE_SIGNAL'
    elif modes[best_any]['total'].get('error_reduction_vs_r300_base',0)>0: verdict='CONTEXT_TEMPORAL_GAIN_UNSAFE'
    else: verdict='CONTEXT_TEMPORAL_NO_SIGNAL'
    out={
      'schema':'deus/arc3-r302-lp85-temporal-residual-context-diagnostic/1','rung':RUNG,'game':TARGET_GAME,
      'lineage':{'r301':'temporal recurrence reduced errors strongly but false changes remained; representation collision is the falsifier'},
      'protocol':{'diagnostic':'p0-p4 only','p5_p19_staged_or_read':False,'past_only_online_history':True,'promotion_in_r302':False},
      'r300_fit_gate':fit,'modes':modes,'safe_modes':safe,'best_safe_mode':best,'best_any_mode':best_any,'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p5_p19_read':False,'independent_hidden_generalization_claim':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r302':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'best_safe_mode':best,'safe_modes':safe,'best_any_mode':best_any,'totals':{k:v['total'] for k,v in modes.items()}},sort_keys=True))

if __name__=='__main__': main()
