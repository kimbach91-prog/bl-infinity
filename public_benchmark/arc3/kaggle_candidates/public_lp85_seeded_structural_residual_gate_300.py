#!/usr/bin/env python3
"""R300: seeded structural-residual expansion for lp85.

R299 found that each of the two R298 hierarchical seed rules anchors a repeated
4-pixel connected residual component on p0-p4 (five occurrences per rule).
R300 freezes one normalized residual template per seed rule from p0-p4 and,
on a source-assisted p5-p9 replay, applies that template only when the exact
hierarchical seed context matches and every expected pre-state cell matches.
Conflicting proposals are discarded. p10-p19 are forbidden.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_hierarchical_sparse_delta_gate_298 as r298
import public_lp85_seeded_structural_residual_diag_299 as r299

TARGET_GAME='lp85-305b61c3'; RUNG=300; MIN_TEMPLATE_SUPPORT=2

def world(board,action): return r275.canon_board(board,action,use_ui_mask=True)

def fit_templates(train_rows,traces):
    seeds,gate=r298.fit_hierarchy(train_rows,traces)
    obs=defaultdict(Counter)
    for ti,tr in enumerate(traces):
        for ri,row in enumerate(tr):
            b=world(row['before'],row['action']); a=world(row['after'],row['action']); h=len(b); w=len(b[0]) if h else 0
            mask=[[int(b[r][c])!=int(a[r][c]) for c in range(w)] for r in range(h)]
            for r in range(h):
                for c in range(w):
                    key=(r298.patch(b,r,c,1),r298.patch(b,r,c,2))
                    if key not in seeds: continue
                    comp=r299.component(mask,r,c)
                    if not comp: continue
                    rel=tuple(sorted((rr-r,cc-c,int(b[rr][cc]),int(a[rr][cc])) for rr,cc in comp))
                    obs[key][rel]+=1
    accepted={}; ambiguous=0
    for key,cnt in obs.items():
        if len(cnt)==1:
            rel,support=next(iter(cnt.items()))
            if support>=MIN_TEMPLATE_SUPPORT: accepted[key]=rel
        else: ambiguous+=1
    return accepted,{'seed_rules':len(seeds),'observed_seed_rules':len(obs),'accepted_templates':len(accepted),'ambiguous_seed_rules':ambiguous,'template_supports':sorted(sum(c.values()) for c in obs.values()),'seed_gate':gate}

def evaluate(rows,templates):
    m=Counter(); per_trace=defaultdict(Counter)
    for row in rows:
        b=world(row['before'],row['action']); a=world(row['after'],row['action']); h=len(b); w=len(b[0]) if h else 0
        proposals=defaultdict(set); t=int(row.get('trace_index',-1))
        for r in range(h):
            for c in range(w):
                key=(r298.patch(b,r,c,1),r298.patch(b,r,c,2))
                rel=templates.get(key)
                if rel is None: continue
                ok=True
                for dr,dc,before,after in rel:
                    rr,cc=r+dr,c+dc
                    if not (0<=rr<h and 0<=cc<w and int(b[rr][cc])==before): ok=False; break
                if not ok: continue
                m['seed_firings']+=1; per_trace[t]['seed_firings']+=1
                for dr,dc,before,after in rel: proposals[(r+dr,c+dc)].add(int(after))
        pred=[list(map(int,x)) for x in b]
        for (r,c),vals in proposals.items():
            if len(vals)==1: pred[r][c]=next(iter(vals))
            else: m['conflicting_cells']+=1; per_trace[t]['conflicting_cells']+=1
        id_err=cand_err=0
        for r in range(h):
            for c in range(w):
                bv=int(b[r][c]); av=int(a[r][c]); pv=int(pred[r][c])
                id_err += bv!=av; cand_err += pv!=av
                if pv!=bv:
                    m['predicted_changes']+=1; per_trace[t]['predicted_changes']+=1
                    if pv==av and bv!=av: m['true_changed_correct']+=1; per_trace[t]['true_changed_correct']+=1
                    elif pv!=av: m['false_changes']+=1; per_trace[t]['false_changes']+=1
        m['frames']+=1; m['pixels']+=h*w; m['identity_errors']+=id_err; m['candidate_errors']+=cand_err
        m['identity_exact_frames']+=id_err==0; m['candidate_exact_frames']+=cand_err==0
    m['identity_pixel_correct']=m['pixels']-m['identity_errors']; m['candidate_pixel_correct']=m['pixels']-m['candidate_errors']
    return dict(m),{str(k):dict(v) for k,v in sorted(per_trace.items())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    traces=[r278.annotated_rows([p]) for p in ps[:5]]; train=[r for tr in traces for r in tr]
    replay=[]
    for idx,p in enumerate(ps[5:],start=5):
        rows=r278.annotated_rows([p])
        for x in rows: x['trace_index']=idx
        replay.extend(rows)
    templates,fit=fit_templates(train,traces); val,per=evaluate(replay,templates)
    exact=val['candidate_exact_frames']-val['identity_exact_frames']; pix=val['candidate_pixel_correct']-val['identity_pixel_correct']
    if val.get('predicted_changes',0)>0 and val.get('false_changes',0)==0 and pix>0: verdict='STRUCTURAL_RESIDUAL_ZERO_FALSE_CHANGE_GAIN'
    elif pix>0: verdict='STRUCTURAL_RESIDUAL_GAIN_WITH_FALSE_CHANGE'
    elif pix<0: verdict='REJECT_STRUCTURAL_RESIDUAL_GATE'
    else: verdict='STRUCTURAL_RESIDUAL_NO_SIGNAL'
    out={'schema':'deus/arc3-r300-lp85-seeded-structural-residual-gate/1','rung':RUNG,'game':TARGET_GAME,
         'lineage':{'r298':'hierarchical seeds replayed 10/10 correct, zero false, +10 pixels, exact-frame delta0','r299':'two train-only repeated connected residual signatures; size4; support5 each'},
         'mechanism':{'seed':'R298 hierarchical 3x3+5x5 gate','expansion':'exact normalized connected residual template learned p0-p4','precondition':'all template before-values must match','conflict_policy':'discard conflicting cell'},
         'protocol':{'fit':'p0-p4 only','source_assisted_replay':'p5-p9 only','p10_p19_staged_or_read':False,'frozen_before_replay':True,'replay_is_not_independent':True,'promotion_in_r300':False},
         'fit_gate':fit,'replay':val,'per_trace':per,'delta':{'exact_frame_delta_vs_identity':exact,'pixel_correct_delta_vs_identity':pix,'error_reduction_vs_identity':val['identity_errors']-val['candidate_errors']},'verdict':verdict,
         'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'p5_p9_replay_is_source_assisted':True,'independent_hidden_generalization_claim':False,'whole_game_policy_claim':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r300':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'verdict':verdict,'fit_gate':fit,'replay':val,'delta':out['delta'],'per_trace':per},sort_keys=True))
if __name__=='__main__': main()
