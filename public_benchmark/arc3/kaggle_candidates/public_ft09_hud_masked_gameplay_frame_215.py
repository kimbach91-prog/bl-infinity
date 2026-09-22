#!/usr/bin/env python3
"""R215: ft09 HUD-masked exact gameplay-frame gate.

R212_FFC proved bottom-row countdown/HUD destroys raw full-frame equality.
R214 showed that HUD timing does not generalize from pre-action bottom-row state.

R215 therefore freezes the same R202 identity + R211 ring2 target-color
composer, but scores exact equality on gameplay rows 0..62 only. Row 63 is
excluded from the metric and is never used to repair predictions.

This is a measurement correction, not a new learned solver.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_mismatch_boarddiff_210 as r210

RUNG=215
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def crop_gameplay(board):
    return [row[:] for row in board[:-1]]

def diff_gameplay(pred,actual,bb):
    # Reuse R210 structural diff on cropped boards with a safe bbox.
    b=list(bb)
    b[2]=min(b[2],len(pred)-2)
    return r210.diff(crop_gameplay(pred),crop_gameplay(actual),tuple(b))

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    im=r212.identity_model(train)
    rm=r212.ring2_model(train)
    s=Counter();by_branch={'identity':Counter(),'ring2_recolor':Counter()}
    wrong=[];resid=Counter()
    for p in held:
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1
            idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
            branch=None;pred=None
            if idkey in im:
                branch='identity';pred=[row[:] for row in r['before']]
            else:
                tgt=rm.get(repr((r['base'],r['ring2'])))
                if tgt is not None:
                    branch='ring2_recolor';pred=r212.recolor_bbox(r['before'],r['bbox'],tgt)
            if pred is None:
                s['abstain']+=1;continue
            s['predictions']+=1;by_branch[branch]['predictions']+=1
            ok=crop_gameplay(pred)==crop_gameplay(r['after'])
            if ok:
                s['correct']+=1;by_branch[branch]['correct']+=1
            else:
                s['wrong']+=1;by_branch[branch]['wrong']+=1
                d=diff_gameplay(pred,r['after'],r['bbox'])
                sig=(d['count'],tuple(d['component_sizes'][:8]),d['inside_clicked_bbox'],tuple(sorted(d['pair_counts'].items())))
                resid[repr(sig)]+=1
                if len(wrong)<30:
                    wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,'current':r.get('current'),'target':r.get('target'),'gameplay_residual':d})
    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in by_branch.items():
        pp=v['predictions'];by_branch[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    gate=bool(p>=100 and metrics.get('accuracy') is not None and metrics['accuracy']>=0.95)
    return {
      'schema':'deus/arc3-ft09-hud-masked-gameplay-frame/1','rung':RUNG,'game':GAME,
      'metric':{'included_rows':'0..62','excluded_rows':[63],'reason':'bottom countdown/HUD is exogenous and R214-falsified as gameplay-predictable state'},
      'heldout':{'all':metrics,'by_branch':by_branch,'residual_signature_counts':dict(resid),'wrong_examples':wrong},
      'gameplay_frame_gate_pass':gate,
      'promotion':{'measurement_gate':gate,'solver_promotion':False,'kaggle_packaging':False,'next_gate':'model only remaining non-HUD scene-transition residual classes'},
      'truth':{
        'public_trace_only':True,'heldout_never_updates_models':True,'hud_row_excluded_from_scoring_only':True,
        'predictions_not_repaired_from_heldout':True,'full_gameplay_frame_measured':True,
        'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False,
      }
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'heldout':d['heldout']['all'],'branches':d['heldout']['by_branch'],'top_residuals':sorted(d['heldout']['residual_signature_counts'].items(),key=lambda x:-x[1])[:10],'gate':d['gameplay_frame_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
