#!/usr/bin/env python3
"""R213: ft09 full-frame composer + deterministic bottom countdown rule.

R212_FFC showed target-color correctness is not enough: the first 40 exact-frame
residuals were all exactly two bottom-row cells changing 12->11, outside the
clicked tile, moving from right to left. R213 adds only that narrow visible-state
rule to the frozen R202+R211 composer.

No heldout outcome updates the identity or ring2 models. The countdown rule is
fixed before this rung evaluates p10-p19. This remains iterative public-heldout
research, not independent generalization or Kaggle execution.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_mismatch_boarddiff_210 as r210

RUNG=213
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def rightmost_timer_pair(board,bb):
    row=board[-1]
    r0,c0,r1,c1,_=bb
    for c in range(len(row)-2,-1,-1):
        if row[c]==12 and row[c+1]==12:
            # Countdown is a separate bottom-row HUD lane; never overwrite click patch.
            if r0<=len(board)-1<=r1 and not (c+1<c0 or c>c1):
                continue
            return (c,c+1)
    return None

def apply_timer(pred,before,bb):
    pair=rightmost_timer_pair(before,bb)
    if pair is None:
        return pred,None
    out=[row[:] for row in pred]
    c0,c1=pair
    out[-1][c0]=11
    out[-1][c1]=11
    return out,pair

def residual_signature(resid):
    return (
        int(resid['count']),
        tuple(resid.get('component_sizes',[])[:8]),
        int(resid.get('bottom4',0)),
        int(resid.get('bottom8',0)),
        int(resid.get('inside_clicked_bbox',0)),
        tuple(sorted(resid.get('pair_counts',{}).items())),
    )

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')
    train=ps[:10]; held=ps[10:]
    im=r212.identity_model(train)
    rm=r212.ring2_model(train)

    s=Counter(); branches={'identity':Counter(),'ring2_recolor_timer':Counter()}
    residuals=Counter(); wrong=[]; correct=[]; timer_applied=0
    for p in held:
        for r in r212.all_rows(p):
            if not r['eligible']:
                continue
            s['eligible']+=1
            import public_ft09_phase_hud_identity_gate_202 as r202
            idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
            branch=None; pred=None; timer_pair=None
            if idkey in im:
                branch='identity'
                pred=[row[:] for row in r['before']]
            else:
                tgt=rm.get(repr((r['base'],r['ring2'])))
                if tgt is not None:
                    branch='ring2_recolor_timer'
                    pred=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                    pred,timer_pair=apply_timer(pred,r['before'],r['bbox'])
                    if timer_pair is not None:
                        timer_applied+=1
            if pred is None:
                s['abstain']+=1
                continue
            s['predictions']+=1; branches[branch]['predictions']+=1
            if pred==r['after']:
                s['correct']+=1; branches[branch]['correct']+=1
                if len(correct)<16:
                    correct.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,'timer_pair':timer_pair})
            else:
                s['wrong']+=1; branches[branch]['wrong']+=1
                resid=r210.diff(pred,r['after'],r['bbox'])
                residuals[repr(residual_signature(resid))]+=1
                if len(wrong)<50:
                    wrong.append({
                        'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,
                        'current':r.get('current'),'target':r.get('target'),
                        'timer_pair':timer_pair,'structural_residual':resid,
                    })

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),
             'exact_accuracy':round(s['correct']/p,6) if p else None,
             'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions']
        branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    gate=bool(p>=100 and metrics.get('exact_accuracy') is not None and metrics['exact_accuracy']>=0.99)
    return {
      'schema':'deus/arc3-ft09-full-frame-countdown-composer/1','rung':RUNG,'game':GAME,
      'lineage':{'identity':'R202 local|s1','target_color':'R211 ring2','full_frame_base':'R212_FFC','new_rule':'rightmost adjacent bottom-row 12,12 -> 11,11 on ring2 branch'},
      'train':{'identity_model_keys':len(im),'ring2_model_keys':len(rm)},
      'heldout':{
        'all':metrics,'by_branch':branches,'timer_applied':timer_applied,
        'residual_signature_counts':dict(residuals),
        'wrong_examples':wrong,'correct_examples':correct,
      },
      'exact_full_frame_gate_pass':gate,
      'promotion':{
        'full_frame_mechanism_gate':gate,
        'solver_promotion':False,
        'kaggle_packaging':False,
        'next_gate':'if residual classes remain, model only the dominant next residual class; otherwise add policy/action coverage',
      },
      'truth':{
        'public_trace_only':True,'iterative_public_heldout_research':True,
        'heldout_never_updates_models':True,'countdown_rule_fixed_before_r213_eval':True,
        'full_frame_predictions_measured':True,'independent_generalization_claim':False,
        'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,action='append',default=[])
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); d=run(a.input)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'heldout':d['heldout']['all'],'branches':d['heldout']['by_branch'],
      'timer_applied':d['heldout']['timer_applied'],
      'top_residuals':sorted(d['heldout']['residual_signature_counts'].items(),key=lambda x:-x[1])[:12],
      'gate':d['exact_full_frame_gate_pass'],'promotion':d['promotion'],
    },sort_keys=True))
if __name__=='__main__': main()
