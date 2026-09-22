#!/usr/bin/env python3
"""Rung 164: object-identity selector for unseen-state full-frame prediction.

Representation change from rung 163: instead of hashing the whole scene into a
coarse relational signature, learn which *object identity class* responds to an
action.  A class is action + board shape + background + literal object color +
translation-invariant same-color 4-connected shape.  A learned displacement may
be instantiated only when exactly one current object matches the class.

The exact one-observation Markov cache from rung 161 remains the baseline.  The
selector is queried only on exact-state cache misses.  A selector program needs
>=2 distinct prior exact states, a unique displacement, and >=2 prior shadow tests
with zero errors before it may affect the candidate.  Current outcome is never
used before the current prediction is locked.  Public pinned trace diagnostic
only; no independent-generalization, solver, GPU, Kaggle, or leaderboard claim.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_object_role_transition_prequential_138 as obj138

RUNG=164
MIN_DISTINCT=2
MIN_SHADOW=2
Grid=list[list[int]]


def obj_key(board:Grid, action:str, obj:obj138.Obj)->str:
    return base.stable({
        'a': action,
        'board_shape': (len(board),len(board[0])),
        'bg': obj138.background_color(board),
        'color': obj.color,
        'shape': obj.shape,
        'area': obj.area,
    })


def delta_key(dr:int,dc:int)->str:
    return base.stable({'dr':int(dr),'dc':int(dc)})


def parse_delta(s:str)->tuple[int,int]|None:
    try:
        d=json.loads(s); return int(d['dr']),int(d['dc'])
    except Exception:
        return None


def unique(counter:Counter[str], support:int=1)->str|None:
    if len(counter)!=1:return None
    k,n=next(iter(counter.items()))
    return k if n>=support else None


def infer_training_program(before:Grid,after:Grid,action:str):
    moved=obj138.infer_pure_translation(before,after)
    if moved is None:return None
    idx,dr,dc=moved
    obs=obj138.objects(before)
    if not (0<=idx<len(obs)):return None
    return obj_key(before,action,obs[idx]),delta_key(dr,dc)


def instantiate(board:Grid,action:str,key:str,delta_s:str)->Grid|None:
    obs=obj138.objects(board)
    matches=[o for o in obs if obj_key(board,action,o)==key]
    if len(matches)!=1:return None
    delta=parse_delta(delta_s)
    if delta is None or delta==(0,0):return None
    return obj138.move_object(board,matches[0],delta[0],delta[1])


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    exact=defaultdict(Counter)
    selector=defaultdict(Counter)
    distinct=defaultdict(set)
    shadow=defaultdict(lambda:{'tests':0,'correct':0,'wrong':0})
    s={
      'transitions':0,'baseline_predictions':0,'baseline_correct':0,'baseline_wrong':0,
      'candidate_predictions':0,'candidate_correct':0,'candidate_wrong':0,
      'added_predictions':0,'added_correct':0,'added_wrong':0,
      'shadow_tests':0,'shadow_correct':0,'shadow_wrong':0,'qualified_predictions':0,
      'pure_translation_training_transitions':0,'selector_contexts_final':0,
      'conflicted_selector_contexts_final':0,
    }
    pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board']); action=base.action_name(e); pre=e
        if not base.same_shape(before,after):continue
        s['transitions']+=1
        kx=r160.context_exact(before,action); target=r160.program(before,after)
        p1=unique(exact[kx],1) if kx in exact else None
        bp=r160.apply_program(before,p1) if p1 is not None else None
        if bp is not None:
            s['baseline_predictions']+=1
            if bp==after:s['baseline_correct']+=1
            else:s['baseline_wrong']+=1
        cp=bp
        if bp is None:
            proposals=[]
            for o in obj138.objects(before):
                ko=obj_key(before,action,o)
                ds=unique(selector[ko],MIN_DISTINCT) if ko in selector and len(distinct[ko])>=MIN_DISTINCT else None
                if ds is None:continue
                pred=instantiate(before,action,ko,ds)
                if pred is None:continue
                proposals.append((ko,ds,pred))
            # Fail closed unless every applicable selector agrees on one frame.
            by_digest={base.digest(p):(k,d,p) for k,d,p in proposals}
            if len(by_digest)==1:
                _dig,(ko,ds,ap)=next(iter(by_digest.items()))
                sh=shadow[(ko,ds)]
                qualified=(sh['tests']>=MIN_SHADOW and sh['wrong']==0)
                if qualified:
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
        # Learn only after current prediction/scoring.
        exact[kx][target]+=1
        tr=infer_training_program(before,after,action)
        if tr is not None:
            ko,ds=tr; selector[ko][ds]+=1; distinct[ko].add(kx); s['pure_translation_training_transitions']+=1
    for prefix in ('baseline','candidate'):
        p=s[prefix+'_predictions'];c=s[prefix+'_correct'];w=s[prefix+'_wrong']
        s[prefix+'_accuracy']=round(c/p,6) if p else None
        s[prefix+'_strict_zero_error']=bool(p and w==0)
    s['shadow_accuracy']=round(s['shadow_correct']/s['shadow_tests'],6) if s['shadow_tests'] else None
    s['selector_contexts_final']=len(selector)
    s['conflicted_selector_contexts_final']=sum(len(v)>1 for v in selector.values())
    return s


def run(paths:list[Path])->dict[str,Any]:
    parts=[audit_trace(base.load_events(p)) for p in paths]
    keys=['transitions','baseline_predictions','baseline_correct','baseline_wrong','candidate_predictions','candidate_correct','candidate_wrong','added_predictions','added_correct','added_wrong','shadow_tests','shadow_correct','shadow_wrong','qualified_predictions','pure_translation_training_transitions']
    agg={k:sum(p[k] for p in parts) for k in keys}
    agg['per_trace_added_correct']=[p['added_correct'] for p in parts]
    agg['per_trace_added_wrong']=[p['added_wrong'] for p in parts]
    agg['per_trace_shadow_tests']=[p['shadow_tests'] for p in parts]
    agg['per_trace_shadow_wrong']=[p['shadow_wrong'] for p in parts]
    agg['strict_gain_p0_p10']=bool(len(parts)>=2 and parts[0]['added_correct']>0 and parts[1]['added_correct']>0 and parts[0]['added_wrong']==0 and parts[1]['added_wrong']==0 and agg['candidate_wrong']==0)
    gate='ZERO_ERROR_P0_P10_OBJECT_IDENTITY_SELECTOR_GAIN' if agg['strict_gain_p0_p10'] else 'NO_STRICT_OBJECT_IDENTITY_SELECTOR_GAIN'
    return {
      'schema':'deus/arc3-public-object-identity-selector/1','rung':RUNG,
      'execution_class':'CPU_PUBLIC_TRACE_PREQUENTIAL_UNSEEN_STATE_OBJECT_SELECTOR_DIAGNOSTIC',
      'representation_change_from_rung163':{'changed':True,'change':'replace coarse whole-scene signature transfer with a learned action-conditioned object identity selector plus executable displacement, queried only on exact-state misses'},
      'parameters':{'min_distinct_exact_states':MIN_DISTINCT,'min_prior_shadow_tests':MIN_SHADOW},
      'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
      'traces':[{'path':str(p),'audit':a} for p,a in zip(paths,parts)],
      'aggregate':agg,'diagnostic_gate':gate,
      'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
      'truth':{
        'public_trace_only':True,'source_assisted_sequence_replay':True,'diagnostic_only':True,
        'exact_cache_misses_only_for_extension':True,'prediction_uses_preaction_and_prior_outcomes_only':True,
        'current_outcome_used_only_for_scoring_and_post_prediction_learning':True,'full_frame_prediction_claim':True,
        'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,
        'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,
        'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False,
      }}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
