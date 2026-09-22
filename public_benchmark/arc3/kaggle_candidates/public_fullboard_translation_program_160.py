#!/usr/bin/env python3
"""Rung 160: prequential translation-normalized full-frame transition programs.

Representation change from rung159: stop guessing which objects move. Learn an
executable board-delta program only from prior outcomes, keyed by the complete
pre-action foreground pattern normalized to its top-left anchor plus action.
The learned program is a list of relative cell edits. At prediction time the
program is instantiated at the current anchor and applied only when every old
cell value matches. Current outcome is revealed only after prediction/scoring.

An exact-state/action replay arm is retained as the conservative baseline. The
normalized arm is promoted only diagnostically when it adds exact full-frame
predictions beyond that baseline without error, including nonzero gain on p0
and p10. Public source-sequence replay only; no Kaggle/model/GPU claim.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138

RUNG=160
MIN_SUPPORT=2
Grid=list[list[int]]


def anchor_and_fg(board:Grid):
    bg=obj138.background_color(board)
    pts=[(r,c,board[r][c]) for r in range(len(board)) for c in range(len(board[0])) if board[r][c]!=bg]
    if not pts:return (0,0),bg,()
    r0=min(r for r,_,_ in pts); c0=min(c for _,c,_ in pts)
    return (r0,c0),bg,tuple(sorted((r-r0,c-c0,v) for r,c,v in pts))


def context_exact(board:Grid,action:str)->str:
    return base.stable({'a':action,'b':board})


def context_norm(board:Grid,action:str)->str:
    (r0,c0),bg,fg=anchor_and_fg(board)
    return base.stable({'a':action,'shape':(len(board),len(board[0])),'bg':bg,'fg':fg})


def program(board:Grid,after:Grid)->str:
    (r0,c0),_bg,_fg=anchor_and_fg(board)
    edits=[]
    for r in range(len(board)):
        for c in range(len(board[0])):
            if board[r][c]!=after[r][c]:edits.append((r-r0,c-c0,board[r][c],after[r][c]))
    return base.stable(edits)


def unique_supported(counter:Counter[str])->str|None:
    if len(counter)!=1:return None
    p,n=next(iter(counter.items()))
    return p if n>=MIN_SUPPORT else None


def apply_program(board:Grid,p:str)->Grid|None:
    try: edits=json.loads(p)
    except Exception:return None
    (r0,c0),_bg,_fg=anchor_and_fg(board); h=len(board); w=len(board[0]); out=[row[:] for row in board]
    for x in edits:
        if not isinstance(x,list) or len(x)!=4:return None
        rr,cc,old,new=map(int,x); r=r0+rr; c=c0+cc
        if not (0<=r<h and 0<=c<w):return None
        if out[r][c]!=old:return None
        out[r][c]=new
    return out


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    exact_bank=defaultdict(Counter); norm_bank=defaultdict(Counter)
    s={k:{'predictions':0,'correct':0,'wrong':0,'abstain':0} for k in ('exact','normalized')}
    s['normalized']['added_predictions_vs_exact']=0; s['normalized']['added_correct_vs_exact']=0; s['normalized']['added_wrong_vs_exact']=0
    pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        before=base.as_grid(pre['board']); after=base.as_grid(e['board']); action=base.action_name(e); pre=e
        if len(before)!=len(after) or len(before[0])!=len(after[0]):continue
        kx=context_exact(before,action); kn=context_norm(before,action); target=program(before,after)
        px=unique_supported(exact_bank[kx]) if kx in exact_bank else None
        pn=unique_supported(norm_bank[kn]) if kn in norm_bank else None
        predx=apply_program(before,px) if px is not None else None
        predn=apply_program(before,pn) if pn is not None else None
        for name,pred in (('exact',predx),('normalized',predn)):
            if pred is None:s[name]['abstain']+=1
            else:
                s[name]['predictions']+=1
                if pred==after:s[name]['correct']+=1
                else:s[name]['wrong']+=1
        if predx is None and predn is not None:
            s['normalized']['added_predictions_vs_exact']+=1
            if predn==after:s['normalized']['added_correct_vs_exact']+=1
            else:s['normalized']['added_wrong_vs_exact']+=1
        exact_bank[kx][target]+=1; norm_bank[kn][target]+=1
    for name in ('exact','normalized'):
        q=s[name]; q['accuracy']=round(q['correct']/q['predictions'],6) if q['predictions'] else None; q['strict_zero_error']=bool(q['predictions'] and q['wrong']==0)
    s['exact_unique_contexts']=len(exact_bank); s['normalized_unique_contexts']=len(norm_bank)
    s['normalized_conflicted_contexts']=sum(len(c)>1 for c in norm_bank.values())
    return s


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    out={}
    for name in ('exact','normalized'):
        pred=sum(p[name]['predictions'] for p in parts); cor=sum(p[name]['correct'] for p in parts); wrong=sum(p[name]['wrong'] for p in parts)
        out[name]={'predictions':pred,'correct':cor,'wrong':wrong,'accuracy':round(cor/pred,6) if pred else None,'strict_zero_error':bool(pred and wrong==0),'per_trace_predictions':[p[name]['predictions'] for p in parts],'per_trace_correct':[p[name]['correct'] for p in parts],'per_trace_wrong':[p[name]['wrong'] for p in parts]}
    added=[p['normalized']['added_correct_vs_exact'] for p in parts]; addw=[p['normalized']['added_wrong_vs_exact'] for p in parts]
    out['normalized_incremental']={'added_correct_vs_exact':sum(added),'added_wrong_vs_exact':sum(addw),'per_trace_added_correct':added,'per_trace_added_wrong':addw,'zero_error_nonzero_p0_p10':bool(len(parts)>=2 and added[0]>0 and added[1]>0 and addw[0]==0 and addw[1]==0 and out['normalized']['wrong']==0)}
    out['per_trace']=parts
    return out


def run(paths:list[Path])->dict[str,Any]:
    parts=[]; traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p)); parts.append(a); traces.append({'path':str(p),'audit':a})
    agg=aggregate(parts); inc=agg['normalized_incremental']
    gate='ZERO_ERROR_P0_P10_TRANSLATION_NORMALIZED_FULLBOARD_GAIN' if inc['zero_error_nonzero_p0_p10'] else 'NO_STRICT_TRANSLATION_NORMALIZED_FULLBOARD_GAIN'
    return {'schema':'deus/arc3-public-fullboard-translation-program/1','rung':RUNG,'execution_class':'CPU_PUBLIC_TRACE_PREQUENTIAL_FULLBOARD_PROGRAM_DIAGNOSTIC','representation_change_from_rung159':{'changed':True,'change':'replace mover-selector guessing with prior-only executable relative cell-edit programs keyed by translation-normalized full pre-action foreground state plus action'},'parameters':{'min_support':MIN_SUPPORT},'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},'traces':traces,'aggregate':agg,'diagnostic_gate':gate,'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'source_assisted_sequence_replay':True,'diagnostic_only':True,'current_prediction_uses_preaction_and_prior_outcomes_only':True,'current_outcome_used_only_for_scoring_and_post_prediction_learning':True,'full_frame_prediction_claim':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}}


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path); args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input); text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end=''); return 0
if __name__=='__main__':raise SystemExit(main())
