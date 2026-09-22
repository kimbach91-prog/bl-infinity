#!/usr/bin/env python3
"""R241: explicit RESET completion gate after R239 for FT09.

R239 is the current public source-assisted zero-wrong transition expert:
1827/1827 exact gameplay predictions over 1982 public actions, leaving
136 level0_animation_click and 19 non_mouse. R240's hidden temporal countdown
model failed and is closed.

The remaining non-mouse action name observed by R240 is exactly RESET. R241
changes mechanism: it does not map arbitrary non-mouse actions to source action
id 0. It recognizes only the explicit public trace action string RESET and
predicts the source-compiled level-0 initial frame. All other non-mouse actions
remain fail-closed. R234/R239 keep precedence for their existing predictions.

Truth boundary: source-assisted/public-trace development transition evidence;
not independent generalization, hidden Kaggle score, provider execution, or
competition submission.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path

import public_ft09_compiled_observation_mechanism_234 as r234
import public_ft09_source_compiled_nonnode_noop_239 as r239

RUNG=241
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def evaluate(paths,manifest):
    levels=manifest['levels']; initial=r234.clone_board(levels[0]['initial_frame'])
    total=Counter(); inc=Counter(); reasons=Counter(); branches=Counter(); examples=[]; wrong=[]
    for p in sorted(paths,key=pnum):
        ev=r234.load_events(p); pre=None
        for e in ev:
            if e.get('board') is None: continue
            if e.get('type')!='action': pre=e; continue
            if pre is None: pre=e; continue
            before=pre['board']; expected=e['board']; action=r234.action_name(e)
            total['eligible']+=1
            pred,meta=r234.predict(before,action,levels); stage='r234'
            if pred is None and meta.get('abstain')=='click_not_unique_node':
                pred2,meta2=r239.fill_nonnode_noop(before,action,levels)
                if pred2 is not None: pred,meta,stage=pred2,meta2,'r239'
                else: pred,meta,stage=None,meta2,'none'
            if pred is None and meta.get('abstain')=='non_mouse' and action.strip().upper()=='RESET':
                pred=r234.clone_board(initial); meta={'branch':'explicit_reset_to_compiled_level0_initial'}; stage='r241'
            if pred is None:
                total['abstain']+=1; reasons[meta.get('abstain','unknown')]+=1; pre=e; continue
            ok=(pred[:-1]==expected[:-1])
            total['predictions']+=1; total['correct' if ok else 'wrong']+=1
            branches[meta.get('branch','unknown')]+=1
            if stage in ('r234','r239'):
                total['anchor_predictions']+=1; total['anchor_correct' if ok else 'anchor_wrong']+=1
            else:
                inc['predictions']+=1; inc['correct' if ok else 'wrong']+=1
                if len(examples)<40: examples.append({'trace':p.name,'action':action,'correct':ok})
            if not ok and len(wrong)<40:
                diff=sum(a!=b for ra,rb in zip(pred[:-1],expected[:-1]) for a,b in zip(ra,rb))
                wrong.append({'trace':p.name,'action':action,'stage':stage,'diff_gameplay_cells':diff})
            pre=e
    assert total['anchor_predictions']==1827,dict(total)
    assert total['anchor_correct']==1827 and total['anchor_wrong']==0,dict(total)
    p=total['predictions']; e=total['eligible']; gate=bool(inc['predictions']>0 and inc['wrong']==0 and total['wrong']==0)
    return {
      'schema':'deus/arc3-ft09-source-compiled-explicit-reset/1','rung':RUNG,'game':GAME,
      'aggregate':{**dict(total),'accuracy':round(total['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0},
      'incremental':{'predictions':inc['predictions'],'correct':inc['correct'],'wrong':inc['wrong'],'examples':examples},
      'branches':dict(branches),'abstain_reasons':dict(reasons),'wrong_examples':wrong,
      'source_assisted_zero_wrong_gain_gate_pass':gate,
      'decision':{
        'source_assisted_transition_expert_promotion':gate,'solver_promotion':False,
        'independent_generalization_promotion':False,'kaggle_packaging':False,
        'next_gate':'if zero-wrong, freeze R241 and address only 136 animation residuals with an observable-state diagnostic; otherwise retain R239',
      },
      'truth':{
        'r239_precedence_preserved':True,'reset_match_is_exact_action_string_only':True,
        'arbitrary_nonmouse_not_mapped_to_source_action0':True,
        'compiled_initial_frame_source_assisted':True,'public_trace_outcomes_do_not_update_manifest':True,
        'gameplay_rows0_62_exact_scoring':True,'independent_generalization_claim':False,
        'hidden_kaggle_score':False,'competition_submission':False,'submission_quota_spent':False,
      },
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); d=evaluate(a.input,json.loads(a.manifest.read_text())); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'aggregate':d['aggregate'],'incremental':{k:v for k,v in d['incremental'].items() if k!='examples'},'branches':d['branches'],'abstain_reasons':d['abstain_reasons'],'gate':d['source_assisted_zero_wrong_gain_gate_pass'],'wrong':d['wrong_examples']},sort_keys=True))
if __name__=='__main__': main()
