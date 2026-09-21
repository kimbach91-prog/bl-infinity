#!/usr/bin/env python3
"""Rung 150: can the rung149 zero-error semantic selector also place the residual?

Rung149 found a pre-outcome action-mobility+phase context that predicts residual
value-pair semantics with zero observed errors and nonzero p0/p10 coverage. This
rung keeps that winning context fixed and adds a second prefix-only lookup for the
*exact residual edits*. Several placement representations are tested, including
absolute coordinates and coordinates anchored to pre-outcome movable/foreground
components; one representation also canonicalizes action direction while retaining
a reversible pre-state anchor.

Prediction order is strict: compute pre-outcome context -> predict semantic from
prior bank -> predict placement keyed by context+predicted semantic from prior bank
-> reveal current outcome -> score -> ingest current semantic/placement. Current
outcome is still required retrospectively to isolate the conservative motion-core
residual and score the target, so this remains source-assisted public replay and is
not yet an independent/full-frame solver result.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_unique_component_motion_audit_140 as motion
import public_residual_shape_canonical_audit_145 as shape145
import public_residual_action_mobility_selector_audit_149 as sel149

RUNG=150
WIN_KEYS=sel149.FEATURE_KEYS['mobility_clearance_bundle']


def residual_edits(before:list[list[int]], after:list[list[int]], action:str) -> tuple[list[tuple[int,int,int,int]], str] | None:
    enc=shape145.encode(before,after,action)
    if not enc['eligible']: return None
    matches=motion.unique_matches(before,after)
    moved=[m for m in matches if (m[2],m[3])!=(0,0)]
    footprint=set()
    for x,y,dr,dc in moved:
        footprint.update(x.cells); footprint.update(y.cells)
    edits=[]
    for r in range(len(before)):
        for c in range(len(before[0])):
            if before[r][c]!=after[r][c] and (r,c) not in footprint:
                edits.append((r,c,before[r][c],after[r][c]))
    if not edits: return None
    return edits, enc['value_pair_multiset']


def movable_anchor(board:list[list[int]],action:str)->tuple[int,int] | None:
    delta=sel149.ACTION_DELTA.get(action.upper())
    if delta is None:return None
    obs=obj138.objects(board); dr,dc=delta
    mov=[o for o in obs if sel149.can_shift(board,o,dr,dc)]
    cells=[p for o in mov for p in o.cells]
    if not cells:return None
    return min(r for r,c in cells), min(c for r,c in cells)


def foreground_anchor(board:list[list[int]])->tuple[int,int] | None:
    bg=obj138.background_color(board)
    pts=[(r,c) for r,row in enumerate(board) for c,v in enumerate(row) if v!=bg]
    if not pts:return None
    return min(r for r,c in pts),min(c for r,c in pts)


def rotate_offset(dr:int,dc:int,action:str)->tuple[int,int]:
    a=action.upper()
    if a=='RIGHT':return dr,dc
    if a=='LEFT':return -dr,-dc
    if a=='DOWN':return -dc,dr
    if a=='UP':return dc,-dr
    return dr,dc


def placement_signatures(before:list[list[int]], edits:list[tuple[int,int,int,int]], action:str)->dict[str,str]:
    r0=min(r for r,c,b,a in edits); c0=min(c for r,c,b,a in edits)
    ma=movable_anchor(before,action); fa=foreground_anchor(before)
    out={
        'absolute':base.stable(edits),
        'residual_normalized':base.stable(sorted((r-r0,c-c0,b,a) for r,c,b,a in edits)),
    }
    if ma is not None:
        mr,mc=ma
        out['movable_anchor']=base.stable(sorted((r-mr,c-mc,b,a) for r,c,b,a in edits))
        out['movable_anchor_action_canonical']=base.stable(sorted((*rotate_offset(r-mr,c-mc,action),b,a) for r,c,b,a in edits))
    if fa is not None:
        fr,fc=fa
        out['foreground_anchor']=base.stable(sorted((r-fr,c-fc,b,a) for r,c,b,a in edits))
    return out


def unique(c:Counter[str])->str|None:
    return next(iter(c)) if len(c)==1 else None


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    reps=('absolute','residual_normalized','movable_anchor','movable_anchor_action_canonical','foreground_anchor')
    semantic_bank:dict[str,Counter[str]]=defaultdict(Counter)
    placement_banks={rep:defaultdict(Counter) for rep in reps}
    stats={rep:{'semantic_predictions':0,'semantic_correct':0,'semantic_wrong':0,'placement_predictions':0,'placement_correct':0,'placement_wrong':0,'placement_unseen':0,'placement_conflict':0} for rep in reps}
    eligible=0; reasons=Counter(); prev1=None; prev2=None; pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        before=base.as_grid(pre['board']);after=base.as_grid(e['board']);action=base.action_name(e);pre=e
        detail=residual_edits(before,after,action)
        if detail is None:
            enc=shape145.encode(before,after,action); reasons[enc.get('reason','residual_detail_missing')]+=1;continue
        edits,target_sem=detail; feat=sel149.mobility_features(before,action)
        if feat is None:reasons['no_mobility_feature']+=1;continue
        eligible+=1
        ctx=base.stable({'f':sel149.project(feat,WIN_KEYS),'p2':prev2,'p1':prev1,'a':action}) if prev2 is not None and prev1 is not None else None
        targets=placement_signatures(before,edits,action)
        sem_pred=unique(semantic_bank[ctx]) if ctx is not None and ctx in semantic_bank else None
        for rep in reps:
            s=stats[rep]
            if sem_pred is not None:
                s['semantic_predictions']+=1
                if sem_pred==target_sem:s['semantic_correct']+=1
                else:s['semantic_wrong']+=1
                pkey=base.stable({'ctx':ctx,'sem':sem_pred})
                if rep not in targets or pkey not in placement_banks[rep]:
                    s['placement_unseen']+=1
                else:
                    pp=unique(placement_banks[rep][pkey])
                    if pp is None:s['placement_conflict']+=1
                    else:
                        s['placement_predictions']+=1
                        if pp==targets[rep]:s['placement_correct']+=1
                        else:s['placement_wrong']+=1
        # Ingest after all predictions lock.
        if ctx is not None:
            semantic_bank[ctx][target_sem]+=1
            true_key=base.stable({'ctx':ctx,'sem':target_sem})
            for rep,val in targets.items():placement_banks[rep][true_key][val]+=1
        prev2,prev1=prev1,target_sem
    for rep,s in stats.items():
        s['semantic_accuracy']=round(s['semantic_correct']/s['semantic_predictions'],6) if s['semantic_predictions'] else None
        s['placement_accuracy']=round(s['placement_correct']/s['placement_predictions'],6) if s['placement_predictions'] else None
        s['placement_coverage_of_eligible']=round(s['placement_predictions']/eligible,6) if eligible else 0.0
        s['strict_zero_error_placement']=bool(s['placement_predictions'] and s['placement_wrong']==0 and s['semantic_wrong']==0)
    return {'eligible_transitions':eligible,'ineligible_reasons':dict(sorted(reasons.items())),'representations':stats}


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    reps=tuple(parts[0]['representations']) if parts else (); eligible=sum(p['eligible_transitions'] for p in parts);out={};hard=[]
    for rep in reps:
        keys=('semantic_predictions','semantic_correct','semantic_wrong','placement_predictions','placement_correct','placement_wrong','placement_unseen','placement_conflict')
        s={k:sum(p['representations'][rep][k] for p in parts) for k in keys}
        pp=[p['representations'][rep]['placement_predictions'] for p in parts];pw=[p['representations'][rep]['placement_wrong'] for p in parts];sw=[p['representations'][rep]['semantic_wrong'] for p in parts]
        s.update({'semantic_accuracy':round(s['semantic_correct']/s['semantic_predictions'],6) if s['semantic_predictions'] else None,'placement_accuracy':round(s['placement_correct']/s['placement_predictions'],6) if s['placement_predictions'] else None,'placement_coverage_of_eligible':round(s['placement_predictions']/eligible,6) if eligible else 0.0,'strict_zero_error_placement':bool(s['placement_predictions'] and s['placement_wrong']==0 and s['semantic_wrong']==0),'per_trace_placement_predictions':pp,'per_trace_placement_wrong':pw,'per_trace_semantic_wrong':sw})
        out[rep]=s
        if pp[0]>0 and pp[1]>0 and pw[0]==0 and pw[1]==0 and sw[0]==0 and sw[1]==0:hard.append((pp[0]+pp[1],rep))
    return {'trace_count':len(parts),'eligible_transitions':eligible,'representations':out,'best_zero_error_p0_p10_placement':max(hard)[1] if hard else None,'per_trace':parts}


def run(paths:list[Path])->dict[str,Any]:
    parts=[];traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p));parts.append(a);traces.append({'path':str(p),'audit':a})
    return {'schema':'deus/arc3-public-residual-placement-reconstruction-audit/1','rung':RUNG,'execution_class':'CPU_PUBLIC_TRACE_RESIDUAL_PLACEMENT_RECONSTRUCTION_DIAGNOSTIC','representation_change_from_rung149':{'changed':True,'change':'compose the fixed zero-error semantic selector with prefix-only exact residual-edit placement lookups, including reversible anchors computed from current pre-outcome state'},'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},'traces':traces,'aggregate':aggregate(parts),'diagnostic_gate':'RESIDUAL_PLACEMENT_RECONSTRUCTION_CHARACTERIZED','promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,'semantic_and_anchor_inputs_available_pre_outcome':True,'current_outcome_used_for_residual_isolation_and_scoring':True,'semantic_prediction_prior_only':True,'placement_prediction_prior_only':True,'current_targets_ingested_after_prediction':True,'hard_trace_gate_requires_p0_and_p10_nonzero_coverage':True,'full_frame_prediction_claim':False,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
