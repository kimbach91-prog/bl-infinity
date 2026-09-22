#!/usr/bin/env python3
"""R243: explicit RESET -> current visible level initial frame for FT09.

R241 tested RESET -> level0 initial and falsified that assumption: 13/19 exact,
6 large cross-level mismatches.  R243 changes only the discriminating mechanism.
For explicit action string RESET, identify the current level from R234 immutable
visible pixels, then return that level's source-compiled initial frame.  If level
identity is unresolved, fail closed.  R234/R239 retain precedence.

Source-assisted public-development transition evidence only; not independent
generalization, provider execution, hidden Kaggle score or submission evidence.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path
import public_ft09_compiled_observation_mechanism_234 as r234
import public_ft09_source_compiled_nonnode_noop_239 as r239
RUNG=243; GAME='ft09-0d8bbf25'
def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name); return int(m.group(1)) if m else -1

def evaluate(paths,manifest):
    levels=manifest['levels']; tot=Counter();inc=Counter();reasons=Counter();branches=Counter();examples=[];wrong=[]
    for p in sorted(paths,key=pnum):
        ev=r234.load_events(p);pre=None
        for e in ev:
            if e.get('board') is None:continue
            if e.get('type')!='action':pre=e;continue
            if pre is None:pre=e;continue
            before=pre['board'];expected=e['board'];action=r234.action_name(e);tot['eligible']+=1
            pred,meta=r234.predict(before,action,levels);stage='r234'
            if pred is None and meta.get('abstain')=='click_not_unique_node':
                p2,m2=r239.fill_nonnode_noop(before,action,levels)
                if p2 is not None:pred,meta,stage=p2,m2,'r239'
                else:pred,meta,stage=None,m2,'none'
            if pred is None and meta.get('abstain')=='non_mouse' and action.strip().upper()=='RESET':
                lev,ident=r234.identify_level(before,levels)
                if lev is not None:
                    pred=r234.clone_board(lev['initial_frame']);meta={'branch':'explicit_reset_to_current_level_initial','level':int(lev['index'])};stage='r243'
                else:
                    meta={'abstain':'reset_level_identification',**ident}
            if pred is None:
                tot['abstain']+=1;reasons[meta.get('abstain','unknown')]+=1;pre=e;continue
            ok=(pred[:-1]==expected[:-1]);tot['predictions']+=1;tot['correct' if ok else 'wrong']+=1;branches[meta.get('branch','unknown')]+=1
            if stage in ('r234','r239'):
                tot['anchor_predictions']+=1;tot['anchor_correct' if ok else 'anchor_wrong']+=1
            else:
                inc['predictions']+=1;inc['correct' if ok else 'wrong']+=1
                if len(examples)<40:examples.append({'trace':p.name,'action':action,'level':meta.get('level'),'correct':ok})
            if not ok and len(wrong)<40:
                diff=sum(a!=b for ra,rb in zip(pred[:-1],expected[:-1]) for a,b in zip(ra,rb))
                wrong.append({'trace':p.name,'action':action,'stage':stage,'level':meta.get('level'),'diff_gameplay_cells':diff})
            pre=e
    assert tot['anchor_predictions']==1827,dict(tot);assert tot['anchor_correct']==1827 and tot['anchor_wrong']==0,dict(tot)
    pp=tot['predictions'];ee=tot['eligible'];gate=bool(inc['predictions']>0 and inc['wrong']==0 and tot['wrong']==0)
    return {'schema':'deus/arc3-ft09-source-compiled-current-level-reset/1','rung':RUNG,'game':GAME,
      'aggregate':{**dict(tot),'accuracy':round(tot['correct']/pp,6) if pp else None,'coverage':round(pp/ee,6) if ee else 0.0},
      'incremental':{'predictions':inc['predictions'],'correct':inc['correct'],'wrong':inc['wrong'],'examples':examples},'branches':dict(branches),'abstain_reasons':dict(reasons),'wrong_examples':wrong,
      'source_assisted_zero_wrong_gain_gate_pass':gate,
      'decision':{'source_assisted_transition_expert_promotion':gate,'solver_promotion':False,'independent_generalization_promotion':False,'kaggle_packaging':False,
                  'next_gate':'if zero-wrong, freeze RESET completion after R239 and compose only with independently verified animation macrostep; otherwise keep R239'},
      'truth':{'r239_precedence_preserved':True,'reset_exact_string_only':True,'current_level_identified_from_visible_static_pixels':True,'compiled_initial_frame_source_assisted':True,
               'public_outcomes_do_not_update_manifest':True,'gameplay_rows0_62_exact_scoring':True,'independent_generalization_claim':False,'hidden_kaggle_score':False,'competition_submission':False,'submission_quota_spent':False}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    d=evaluate(a.input,json.loads(a.manifest.read_text()));a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'aggregate':d['aggregate'],'incremental':{k:v for k,v in d['incremental'].items() if k!='examples'},'branches':d['branches'],'abstain_reasons':d['abstain_reasons'],'gate':d['source_assisted_zero_wrong_gain_gate_pass'],'wrong':d['wrong_examples']},sort_keys=True))
if __name__=='__main__':main()
