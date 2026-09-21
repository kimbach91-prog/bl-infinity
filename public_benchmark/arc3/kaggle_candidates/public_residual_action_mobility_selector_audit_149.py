#!/usr/bin/env python3
"""Rung 149: action-conditioned causal mobility selectors for residual semantics.

Rung 148 restored p0/p10 coverage with coarse state summaries but retained errors.
This rung changes representation toward the causal motion core from rung141: before
seeing the outcome, segment non-background components and ask which components can
legally translate by the known directional action delta (3 cells) without leaving
the board or colliding with other foreground. The selector summarizes movable vs
blocked components by counts/colors/areas, optionally with prior-two residual
semantic phase.

The semantic target is still the residual before->after value-pair multiset from
rung145. Current outcome is used retrospectively only to isolate the eligible
motion-core residual and score target. Contexts are computed from current pre-
outcome state/action and prior targets; current target is ingested after prediction.
Diagnostic only; no exact-frame/solver/model/GPU/Kaggle claim.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_residual_shape_canonical_audit_145 as shape145

RUNG = 149
ACTION_DELTA = {'UP':(-3,0),'DOWN':(3,0),'LEFT':(0,-3),'RIGHT':(0,3)}


def can_shift(board: list[list[int]], obj: obj138.Obj, dr: int, dc: int) -> bool:
    h,w=len(board),len(board[0]); bg=obj138.background_color(board)
    src=set(obj.cells); dst={(r+dr,c+dc) for r,c in src}
    if any(r<0 or r>=h or c<0 or c>=w for r,c in dst): return False
    return all((r,c) in src or board[r][c]==bg for r,c in dst)


def mobility_features(board: list[list[int]], action: str) -> dict[str, Any] | None:
    delta=ACTION_DELTA.get(action.upper())
    if delta is None: return None
    obs=obj138.objects(board); dr,dc=delta
    movable=[o for o in obs if can_shift(board,o,dr,dc)]
    blocked=[o for o in obs if not can_shift(board,o,dr,dc)]
    mc=Counter(o.color for o in movable); bc=Counter(o.color for o in blocked)
    return {
        'counts': (len(obs),len(movable),len(blocked)),
        'movable_color_counts': tuple(sorted(mc.items())),
        'blocked_color_counts': tuple(sorted(bc.items())),
        'movable_areas0': tuple(sorted(o.area for o in movable)),
        'blocked_areas0': tuple(sorted(o.area for o in blocked)),
        'movable_areas_color': tuple(sorted((o.color,o.area) for o in movable)),
        'edge_clearance_bins': tuple(sorted((min(o.r0, len(board)-1-o.r1, o.c0, len(board[0])-1-o.c1), o.area) for o in movable)),
    }


def single(c: Counter[str]) -> str | None:
    return next(iter(c)) if len(c)==1 else None

FEATURE_KEYS={
    'mobility_counts': ('counts',),
    'movable_color_counts': ('movable_color_counts',),
    'movable_areas0': ('movable_areas0',),
    'movable_areas_color': ('movable_areas_color',),
    'mobility_color_bundle': ('counts','movable_color_counts','blocked_color_counts'),
    'mobility_area_bundle': ('counts','movable_areas0','blocked_areas0'),
    'mobility_clearance_bundle': ('counts','movable_areas0','edge_clearance_bins'),
}


def project(feat: dict[str,Any], keys: tuple[str,...]) -> Any:
    return tuple((k,feat[k]) for k in keys)


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    names=tuple([f'{n}_action' for n in FEATURE_KEYS]+[f'{n}_prev2_action' for n in FEATURE_KEYS])
    banks: dict[str,dict[str,Counter[str]]]={n:defaultdict(Counter) for n in names}
    stats={n:{'predictions':0,'correct':0,'wrong':0,'conflict_abstentions':0,'unseen_abstentions':0} for n in names}
    eligible=0; reasons=Counter(); prev1=None; prev2=None; pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action': pre=e; continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board']); action=base.action_name(e)
        enc=shape145.encode(before,after,action); pre=e
        if not enc['eligible']:
            reasons[enc['reason']]+=1; continue
        feat=mobility_features(before,action)
        if feat is None:
            reasons['no_mobility_feature']+=1; continue
        eligible+=1; target=enc['value_pair_multiset']; contexts={}
        for fname,keys in FEATURE_KEYS.items():
            f=project(feat,keys)
            contexts[f'{fname}_action']=base.stable({'f':f,'a':action})
            contexts[f'{fname}_prev2_action']=base.stable({'f':f,'p2':prev2,'p1':prev1,'a':action}) if prev2 is not None and prev1 is not None else None
        for name,key in contexts.items():
            if key is None or key not in banks[name]: stats[name]['unseen_abstentions']+=1; continue
            pred=single(banks[name][key])
            if pred is None: stats[name]['conflict_abstentions']+=1; continue
            stats[name]['predictions']+=1
            if pred==target: stats[name]['correct']+=1
            else: stats[name]['wrong']+=1
        for name,key in contexts.items():
            if key is not None: banks[name][key][target]+=1
        prev2,prev1=prev1,target
    for name,s in stats.items():
        s['accuracy']=round(s['correct']/s['predictions'],6) if s['predictions'] else None
        s['coverage_of_eligible']=round(s['predictions']/eligible,6) if eligible else 0.0
        s['strict_zero_error']=bool(s['predictions'] and s['wrong']==0)
        s['unique_contexts_final']=len(banks[name])
        s['conflicted_contexts_final']=sum(len(c)>1 for c in banks[name].values())
    return {'eligible_transitions':eligible,'ineligible_reasons':dict(sorted(reasons.items())),'contexts':stats}


def aggregate(parts: list[dict[str,Any]]) -> dict[str,Any]:
    names=tuple(parts[0]['contexts']) if parts else (); eligible=sum(p['eligible_transitions'] for p in parts); out={}; hard=[]
    for name in names:
        pred=sum(p['contexts'][name]['predictions'] for p in parts); correct=sum(p['contexts'][name]['correct'] for p in parts); wrong=sum(p['contexts'][name]['wrong'] for p in parts)
        pp=[p['contexts'][name]['predictions'] for p in parts]; pw=[p['contexts'][name]['wrong'] for p in parts]
        out[name]={'predictions':pred,'correct':correct,'wrong':wrong,'accuracy':round(correct/pred,6) if pred else None,'coverage_of_eligible':round(pred/eligible,6) if eligible else 0.0,'strict_zero_error':bool(pred and wrong==0),'per_trace_predictions':pp,'per_trace_wrong':pw}
        if pp[0]>0 and pp[1]>0 and pw[0]==0 and pw[1]==0: hard.append((pp[0]+pp[1],name))
    return {'trace_count':len(parts),'eligible_transitions':eligible,'contexts':out,'best_zero_error_p0_p10_context':max(hard)[1] if hard else None,'per_trace':parts}


def run(paths:list[Path])->dict[str,Any]:
    parts=[];traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p));parts.append(a);traces.append({'path':str(p),'audit':a})
    return {'schema':'deus/arc3-public-residual-action-mobility-selector-audit/1','rung':RUNG,'execution_class':'CPU_PUBLIC_TRACE_RESIDUAL_ACTION_MOBILITY_SELECTOR_DIAGNOSTIC','representation_change_from_rung148':{'changed':True,'change':'replace generic coarse state lookup with pre-outcome action-conditioned legal-translation mobility/precondition summaries of connected components'},'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},'traces':traces,'aggregate':aggregate(parts),'diagnostic_gate':'RESIDUAL_ACTION_MOBILITY_SELECTOR_CHARACTERIZED','promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,'selector_features_available_pre_outcome':True,'current_outcome_used_for_regime_isolation_and_target_scoring':True,'prediction_context_prior_only':True,'current_target_ingested_after_prediction':True,'hard_trace_gate_requires_p0_and_p10_nonzero_coverage':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
