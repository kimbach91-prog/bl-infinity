#!/usr/bin/env python3
"""Rung 161: one-observation Markov cache audit for exact full-frame prediction.

Rung160 showed 370/370 exact full-frame predictions at support>=2 and no benefit
from translation normalization. This rung changes the reliability representation:
a complete visible state+action is treated as a candidate deterministic Markov
key after one prior observation, but a key is invalidated for future prediction
as soon as conflicting transition programs are observed. The current outcome is
never used before the current prediction is locked.

The support>=2 policy from rung160 remains the baseline. Promotion is diagnostic
only if the support>=1 conflict-invalidating cache adds zero-error full-frame
predictions on both p0 and p10. Public sequence replay only; no Kaggle claim.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160

RUNG=161


def unique(c:Counter[str],support:int)->str|None:
    if len(c)!=1:return None
    p,n=next(iter(c.items()))
    return p if n>=support else None


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    bank=defaultdict(Counter)
    stats={k:{'predictions':0,'correct':0,'wrong':0,'abstain':0} for k in ('support2','support1')}
    stats['support1'].update({'added_predictions_vs_support2':0,'added_correct_vs_support2':0,'added_wrong_vs_support2':0})
    pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board']); action=base.action_name(e); pre=e
        if len(before)!=len(after) or len(before[0])!=len(after[0]):continue
        key=r160.context_exact(before,action); target=r160.program(before,after)
        p2=unique(bank[key],2) if key in bank else None; p1=unique(bank[key],1) if key in bank else None
        pred2=r160.apply_program(before,p2) if p2 is not None else None; pred1=r160.apply_program(before,p1) if p1 is not None else None
        for name,pred in (('support2',pred2),('support1',pred1)):
            if pred is None:stats[name]['abstain']+=1
            else:
                stats[name]['predictions']+=1
                if pred==after:stats[name]['correct']+=1
                else:stats[name]['wrong']+=1
        if pred2 is None and pred1 is not None:
            stats['support1']['added_predictions_vs_support2']+=1
            if pred1==after:stats['support1']['added_correct_vs_support2']+=1
            else:stats['support1']['added_wrong_vs_support2']+=1
        bank[key][target]+=1
    for n in ('support2','support1'):
        s=stats[n]; s['accuracy']=round(s['correct']/s['predictions'],6) if s['predictions'] else None; s['strict_zero_error']=bool(s['predictions'] and s['wrong']==0)
    stats['unique_contexts_final']=len(bank); stats['conflicted_contexts_final']=sum(len(c)>1 for c in bank.values())
    return stats


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    out={}
    for n in ('support2','support1'):
        pred=sum(p[n]['predictions'] for p in parts); cor=sum(p[n]['correct'] for p in parts); wrong=sum(p[n]['wrong'] for p in parts)
        out[n]={'predictions':pred,'correct':cor,'wrong':wrong,'accuracy':round(cor/pred,6) if pred else None,'strict_zero_error':bool(pred and wrong==0),'per_trace_predictions':[p[n]['predictions'] for p in parts],'per_trace_correct':[p[n]['correct'] for p in parts],'per_trace_wrong':[p[n]['wrong'] for p in parts]}
    ac=[p['support1']['added_correct_vs_support2'] for p in parts]; aw=[p['support1']['added_wrong_vs_support2'] for p in parts]
    out['incremental']={'added_correct_vs_support2':sum(ac),'added_wrong_vs_support2':sum(aw),'per_trace_added_correct':ac,'per_trace_added_wrong':aw,'zero_error_nonzero_p0_p10':bool(len(parts)>=2 and ac[0]>0 and ac[1]>0 and aw[0]==0 and aw[1]==0 and out['support1']['wrong']==0)}
    out['conflicted_contexts_final']=sum(p['conflicted_contexts_final'] for p in parts); out['per_trace']=parts
    return out


def run(paths:list[Path])->dict[str,Any]:
    parts=[]; traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p));parts.append(a);traces.append({'path':str(p),'audit':a})
    agg=aggregate(parts); gate='ZERO_ERROR_P0_P10_ONE_SHOT_MARKOV_FULLBOARD_GAIN' if agg['incremental']['zero_error_nonzero_p0_p10'] else 'NO_STRICT_ONE_SHOT_MARKOV_FULLBOARD_GAIN'
    return {'schema':'deus/arc3-public-fullboard-markov-cache/1','rung':RUNG,'execution_class':'CPU_PUBLIC_TRACE_PREQUENTIAL_FULLBOARD_MARKOV_CACHE_DIAGNOSTIC','representation_change_from_rung160':{'changed':True,'change':'replace arbitrary support>=2 requirement with a complete-visible-state/action deterministic Markov key after one prior transition, fail-closing future predictions on observed conflict'},'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},'traces':traces,'aggregate':agg,'diagnostic_gate':gate,'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'source_assisted_sequence_replay':True,'diagnostic_only':True,'prediction_uses_current_visible_state_action_and_prior_outcomes_only':True,'current_outcome_used_only_for_scoring_and_post_prediction_learning':True,'full_frame_prediction_claim':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
