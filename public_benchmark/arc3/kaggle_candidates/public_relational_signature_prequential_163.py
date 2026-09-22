#!/usr/bin/env python3
"""Rung 163: prequential relational-signature executable full-frame programs.

R161 memorizes complete visible state+action after one prior deterministic outcome.
This rung only attempts extension when that exact key is unseen.  It groups prior
states by action plus board dimensions, background, foreground bbox dimensions and
color histogram, deliberately discarding absolute placement and detailed geometry.
The executable target remains the relative cell-edit program from rung160.  An
abstract program may affect prediction only after support from >=2 distinct exact
states and >=3 prior shadow tests with zero error.  Current outcome is scored before
it is learned. Public pinned trace diagnostic only; no Kaggle/generalization claim.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any
import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160

RUNG=163
MIN_DISTINCT=2
MIN_SHADOW=3
Grid=list[list[int]]

def relational_key(board:Grid,action:str)->str:
    (_anchor,bg,_fg)=r160.anchor_and_fg(board)
    pts=[(r,c,board[r][c]) for r in range(len(board)) for c in range(len(board[0])) if board[r][c]!=bg]
    if pts:
        rs=[r for r,_,_ in pts]; cs=[c for _,c,_ in pts]
        bbox=(max(rs)-min(rs)+1,max(cs)-min(cs)+1)
    else:bbox=(0,0)
    hist=sorted(Counter(v for row in board for v in row if v!=bg).items())
    return base.stable({'a':action,'shape':(len(board),len(board[0])),'bg':bg,'bbox':bbox,'hist':hist})

def unique(counter:Counter[str])->str|None:
    if len(counter)!=1:return None
    return next(iter(counter))

def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    exact=defaultdict(Counter)
    abstract=defaultdict(Counter)
    distinct=defaultdict(set)
    shadow=defaultdict(lambda:{'tests':0,'correct':0,'wrong':0})
    s={'transitions':0,'baseline_predictions':0,'baseline_correct':0,'baseline_wrong':0,
       'candidate_predictions':0,'candidate_correct':0,'candidate_wrong':0,
       'added_predictions':0,'added_correct':0,'added_wrong':0,
       'shadow_tests':0,'shadow_correct':0,'shadow_wrong':0,
       'qualified_predictions':0,'abstract_contexts_final':0,'conflicted_abstract_contexts_final':0}
    pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board']); action=base.action_name(e); pre=e
        if not base.same_shape(before,after):continue
        s['transitions']+=1
        kx=r160.context_exact(before,action); ka=relational_key(before,action); target=r160.program(before,after)
        bx=unique(exact[kx]) if kx in exact else None
        bp=r160.apply_program(before,bx) if bx is not None else None
        if bp is not None:
            s['baseline_predictions']+=1
            if bp==after:s['baseline_correct']+=1
            else:s['baseline_wrong']+=1
        cp=bp
        pa=unique(abstract[ka]) if ka in abstract else None
        eligible=(bp is None and pa is not None and len(distinct[ka])>=MIN_DISTINCT)
        ap=r160.apply_program(before,pa) if eligible else None
        if eligible and ap is not None:
            sh=shadow[ka]
            if sh['tests']>=MIN_SHADOW and sh['wrong']==0:
                cp=ap;s['qualified_predictions']+=1
            s['shadow_tests']+=1;sh['tests']+=1
            if ap==after:s['shadow_correct']+=1;sh['correct']+=1
            else:s['shadow_wrong']+=1;sh['wrong']+=1
        if cp is not None:
            s['candidate_predictions']+=1
            if cp==after:s['candidate_correct']+=1
            else:s['candidate_wrong']+=1
        if bp is None and cp is not None:
            s['added_predictions']+=1
            if cp==after:s['added_correct']+=1
            else:s['added_wrong']+=1
        exact[kx][target]+=1;abstract[ka][target]+=1;distinct[ka].add(kx)
    for prefix in ('baseline','candidate'):
        p=s[prefix+'_predictions'];c=s[prefix+'_correct'];w=s[prefix+'_wrong']
        s[prefix+'_accuracy']=round(c/p,6) if p else None;s[prefix+'_strict_zero_error']=bool(p and w==0)
    s['shadow_accuracy']=round(s['shadow_correct']/s['shadow_tests'],6) if s['shadow_tests'] else None
    s['abstract_contexts_final']=len(abstract);s['conflicted_abstract_contexts_final']=sum(len(v)>1 for v in abstract.values())
    return s

def run(paths:list[Path])->dict[str,Any]:
    parts=[audit_trace(base.load_events(p)) for p in paths]
    def sums(k):return [p[k] for p in parts]
    agg={k:sum(sums(k)) for k in ['transitions','baseline_predictions','baseline_correct','baseline_wrong','candidate_predictions','candidate_correct','candidate_wrong','added_predictions','added_correct','added_wrong','shadow_tests','shadow_correct','shadow_wrong','qualified_predictions']}
    agg['per_trace_added_correct']=sums('added_correct');agg['per_trace_added_wrong']=sums('added_wrong');agg['per_trace_candidate_wrong']=sums('candidate_wrong')
    agg['strict_gain_p0_p10']=bool(len(parts)>=2 and parts[0]['added_correct']>0 and parts[1]['added_correct']>0 and parts[0]['added_wrong']==0 and parts[1]['added_wrong']==0 and agg['candidate_wrong']==0)
    gate='ZERO_ERROR_P0_P10_RELATIONAL_SIGNATURE_GAIN' if agg['strict_gain_p0_p10'] else 'NO_STRICT_RELATIONAL_SIGNATURE_GAIN'
    return {'schema':'deus/arc3-public-relational-signature-prequential/1','rung':RUNG,
      'execution_class':'CPU_PUBLIC_TRACE_PREQUENTIAL_UNSEEN_STATE_EXECUTABLE_DIAGNOSTIC',
      'representation_change_from_rung161':{'changed':True,'change':'on exact-state cache misses, transfer relative edit programs through a coarse placement-discarding relational signature, gated by distinct-state support and prior zero-error shadow tests'},
      'parameters':{'min_distinct_exact_states':MIN_DISTINCT,'min_prior_shadow_tests':MIN_SHADOW},
      'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
      'traces':[{'path':str(p),'audit':a} for p,a in zip(paths,parts)],'aggregate':agg,'diagnostic_gate':gate,
      'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
      'truth':{'public_trace_only':True,'source_assisted_sequence_replay':True,'diagnostic_only':True,'exact_cache_misses_only_for_extension':True,'prediction_uses_preaction_and_prior_outcomes_only':True,'current_outcome_used_only_for_scoring_and_post_prediction_learning':True,'full_frame_prediction_claim':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
